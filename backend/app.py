import os
import shutil
import asyncio
import subprocess
from typing import Optional, List, Dict, Any
from urllib.parse import quote

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.downloader import (
    extract_media_info,
    DOWNLOADS_DIR,
    format_bytes
)
from backend.task_manager import task_manager
from backend.cookie_manager import cookie_manager
from backend.ffmpeg_helper import get_ffmpeg_path, get_ffmpeg_version
import yt_dlp

app = FastAPI(title="UniDownloader API", version="2.0.0")

# Включаем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модели Pydantic
class ExtractRequest(BaseModel):
    url: str
    cookie_type: str = "none" # "none", "file", "browser"
    cookie_value: Optional[str] = None
    proxy: Optional[str] = None
    is_playlist: bool = False

class DownloadRequest(BaseModel):
    url: str
    title: Optional[str] = "Медиа файл"
    thumbnail: Optional[str] = None
    download_type: str = "video" # "video", "audio", "subtitle"
    quality: str = "best"
    output_format: str = "mp4"
    video_codec: str = "copy" # "copy", "h264", "hevc", "vp9", "av1"
    sub_lang: Optional[str] = None
    embed_subs: bool = False
    cookie_type: str = "none"
    cookie_value: Optional[str] = None
    proxy: Optional[str] = None

class BatchDownloadRequest(BaseModel):
    items: List[Dict[str, Any]]
    download_type: str = "video"
    quality: str = "best"
    output_format: str = "mp4"
    video_codec: str = "copy"
    sub_lang: Optional[str] = None
    cookie_type: str = "none"
    cookie_value: Optional[str] = None
    proxy: Optional[str] = None

class PlaylistZipRequest(BaseModel):
    title: str
    items: List[Dict[str, Any]]
    download_type: str = "audio" # "audio" | "video"
    quality: str = "mp3_320"
    output_format: str = "mp3"   # "mp3" | "mp4" | etc.
    video_codec: str = "copy"
    cookie_type: str = "none"
    cookie_value: Optional[str] = None
    proxy: Optional[str] = None

class SaveCookieTextRequest(BaseModel):
    name: str
    content: str

# API Эндпоинты

@app.post("/api/extract")
async def api_extract_info(req: ExtractRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="Укажите URL для скачивания")

    try:
        # Запускаем в отдельном потоке, чтобы не блокировать event loop
        info = await asyncio.to_thread(
            extract_media_info,
            url=req.url.strip(),
            cookie_type=req.cookie_type,
            cookie_value=req.cookie_value,
            proxy=req.proxy,
            is_playlist=req.is_playlist
        )
        return info
    except Exception as e:
        error_text = str(e)
        if "Sign in to confirm your age" in error_text:
            error_text = "Видео имеет ограничение 18+. Подключите Cookies в настройках (кнопка 'Куки 🍪')."
        elif "Private video" in error_text:
            error_text = "Приватное видео. Требуются Cookies с авторизацией."
        elif "Video unavailable" in error_text:
            error_text = "Видео недоступно или удалено."
        elif "HTTP Error 429" in error_text:
            error_text = "Слишком много запросов (Rate Limit). Попробуйте использовать Proxy или Cookies."
        raise HTTPException(status_code=400, detail=error_text)

@app.post("/api/download")
async def api_start_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="Укажите URL")

    task_id = task_manager.create_task(
        url=req.url.strip(),
        title=req.title or "Медиа файл",
        thumbnail=req.thumbnail,
        download_type=req.download_type,
        quality=req.quality,
        output_format=req.output_format,
        video_codec=req.video_codec,
        sub_lang=req.sub_lang,
        embed_subs=req.embed_subs,
        cookie_type=req.cookie_type,
        cookie_value=req.cookie_value,
        proxy=req.proxy
    )

    loop = asyncio.get_event_loop()
    # Запускаем фоновую задачу
    asyncio.create_task(task_manager.start_download_task(task_id, loop))

    return {"success": True, "task_id": task_id, "status": "queued"}

@app.post("/api/batch-download")
async def api_batch_download(req: BatchDownloadRequest):
    if not req.items:
        raise HTTPException(status_code=400, detail="Список элементов пуст")

    task_ids = []
    loop = asyncio.get_event_loop()

    for item in req.items:
        url = item.get("url")
        if not url:
            continue
        title = item.get("title") or "Видео из плейлиста"
        thumbnail = item.get("thumbnail")

        task_id = task_manager.create_task(
            url=url.strip(),
            title=title,
            thumbnail=thumbnail,
            download_type=req.download_type,
            quality=req.quality,
            output_format=req.output_format,
            video_codec=req.video_codec,
            sub_lang=req.sub_lang,
            cookie_type=req.cookie_type,
            cookie_value=req.cookie_value,
            proxy=req.proxy
        )
        task_ids.append(task_id)
        asyncio.create_task(task_manager.start_download_task(task_id, loop))

    return {"success": True, "task_ids": task_ids, "count": len(task_ids)}

@app.post("/api/playlist/download-zip")
async def api_download_playlist_zip(req: PlaylistZipRequest):
    if not req.items:
        raise HTTPException(status_code=400, detail="Список элементов пуст")

    task_id = task_manager.create_task(
        url=req.items[0].get("url", ""),
        title=f"📦 [ZIP] {req.title} ({len(req.items)} файлов)",
        thumbnail=req.items[0].get("thumbnail"),
        download_type="zip",
        quality=req.quality,
        output_format="zip",
        video_codec=req.video_codec,
        cookie_type=req.cookie_type,
        cookie_value=req.cookie_value,
        proxy=req.proxy
    )

    loop = asyncio.get_event_loop()
    asyncio.create_task(
        task_manager.start_playlist_zip_task(
            task_id=task_id,
            items=req.items,
            playlist_title=req.title,
            download_type=req.download_type,
            quality=req.quality,
            output_format=req.output_format,
            video_codec=req.video_codec,
            cookie_type=req.cookie_type,
            cookie_value=req.cookie_value,
            proxy=req.proxy,
            loop=loop
        )
    )

    return {"success": True, "task_id": task_id, "status": "queued"}

@app.get("/api/task/{task_id}")
async def api_get_task(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task

@app.get("/api/history")
async def api_get_history():
    return task_manager.get_history()

@app.delete("/api/history/{item_id}")
async def api_delete_history(item_id: str):
    success = task_manager.delete_history_item(item_id)
    return {"success": success}

@app.get("/api/cookies")
async def api_get_cookies():
    return {
        "profiles": cookie_manager.list_profiles(),
        "browsers": cookie_manager.get_supported_browsers()
    }

@app.post("/api/cookies/upload")
async def api_upload_cookie_file(file: UploadFile = File(...), name: Optional[str] = Form(None)):
    contents = await file.read()
    profile_name = name or file.filename or "cookies.txt"
    profile = cookie_manager.save_cookie_file(profile_name, contents)
    return {"success": True, "profile": profile}

@app.post("/api/cookies/save-text")
async def api_save_cookie_text(req: SaveCookieTextRequest):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Содержимое cookies не может быть пустым")
    profile = cookie_manager.save_cookie_text(req.name or "cookies", req.content)
    return {"success": True, "profile": profile}

@app.delete("/api/cookies/{profile_id}")
async def api_delete_cookie(profile_id: str):
    success = cookie_manager.delete_profile(profile_id)
    return {"success": success}

@app.get("/api/download-file/{file_id}")
async def api_serve_file(file_id: str, inline: bool = False):
    # Ищем в истории или напрямую в папке downloads
    history = task_manager.get_history()
    target_filepath = None
    target_filename = None

    for item in history:
        if item["id"] == file_id or item.get("filename") == file_id:
            target_filepath = item.get("filepath")
            target_filename = item.get("filename")
            break

    if not target_filepath or not os.path.exists(target_filepath):
        # Проверяем напрямую по имени файла в downloads
        direct_path = os.path.join(DOWNLOADS_DIR, file_id)
        if os.path.exists(direct_path):
            target_filepath = direct_path
            target_filename = file_id

    if not target_filepath or not os.path.exists(target_filepath):
        raise HTTPException(status_code=404, detail="Файл не найден на сервере")

    # Определение MIME типа
    ext = os.path.splitext(target_filepath)[1].lower()
    media_types = {
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
        ".wav": "audio/wav",
        ".opus": "audio/opus",
        ".ogg": "audio/ogg",
        ".zip": "application/zip",
        ".srt": "text/plain",
        ".vtt": "text/vtt",
        ".ass": "text/plain",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    # Отдача файла с корректной поддержкой UTF-8 в именах файлов
    fallback_name = target_filename or os.path.basename(target_filepath)
    return FileResponse(
        target_filepath,
        media_type=media_type,
        filename=fallback_name,
        content_disposition_type="inline" if inline else "attachment"
    )

@app.get("/api/system-info")
async def api_get_system_info():
    ffmpeg_p = get_ffmpeg_path()
    ffmpeg_v = get_ffmpeg_version()

    # Свободное место на диске
    total, used, free = shutil.disk_usage(DOWNLOADS_DIR)

    ytdlp_ver = "2026.x"
    try:
        import yt_dlp.version
        ytdlp_ver = yt_dlp.version.__version__
    except Exception:
        pass

    return {
        "ytdlp_version": ytdlp_ver,
        "ffmpeg_path": ffmpeg_p,
        "ffmpeg_version": ffmpeg_v,
        "downloads_dir": DOWNLOADS_DIR,
        "disk_free": format_bytes(free),
        "disk_total": format_bytes(total),
        "disk_used": format_bytes(used),
    }

@app.post("/api/update-ytdlp")
async def api_update_ytdlp():
    try:
        import sys
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        return {"success": True, "output": res.stdout or res.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

# WebSocket для живого обновления прогресса задач
@app.websocket("/ws/tasks")
async def websocket_tasks_endpoint(websocket: WebSocket):
    await task_manager.register_websocket(websocket)
    try:
        while True:
            # Слушаем ping/сообщения от клиента
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        task_manager.unregister_websocket(websocket)
    except Exception:
        task_manager.unregister_websocket(websocket)

from backend.path_utils import get_static_dir

# Статические файлы фронтенда
STATIC_DIR = get_static_dir()
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)

# Монтируем директорию со статикой
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>UniDownloader Frontend Loading...</h1>")
