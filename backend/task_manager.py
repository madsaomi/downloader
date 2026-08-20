import os
import json
import time
import uuid
import shutil
import zipfile
import asyncio
from typing import Dict, Any, List, Optional, Set
from fastapi import WebSocket

from backend.downloader import download_media_item, format_bytes, sanitize_filename, DOWNLOADS_DIR

HISTORY_FILE = os.path.join(DOWNLOADS_DIR, "history.json")

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.active_websockets: Set[WebSocket] = set()
        self.history: List[Dict[str, Any]] = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    valid_items = []
                    for item in data:
                        fp = item.get("filepath")
                        if fp and os.path.exists(fp):
                            item["filesize"] = os.path.getsize(fp)
                            item["filesize_formatted"] = format_bytes(item["filesize"])
                            valid_items.append(item)
                    return valid_items
            except Exception:
                return []
        return []

    def _save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history[:100], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    async def register_websocket(self, websocket: WebSocket):
        await websocket.accept()
        self.active_websockets.add(websocket)
        active_tasks = [t for t in self.tasks.values() if t.get("status") in ["queued", "downloading", "processing"]]
        if active_tasks:
            try:
                await websocket.send_json({"type": "initial_tasks", "tasks": active_tasks})
            except Exception:
                pass

    def unregister_websocket(self, websocket: WebSocket):
        self.active_websockets.discard(websocket)

    async def broadcast_task_update(self, task_data: Dict[str, Any]):
        if not self.active_websockets:
            return
        msg = {"type": "task_update", "task": task_data}
        dead_sockets = set()
        for ws in list(self.active_websockets):
            try:
                await ws.send_json(msg)
            except Exception:
                dead_sockets.add(ws)
        for ws in dead_sockets:
            self.active_websockets.discard(ws)

    def create_task(
        self,
        url: str,
        title: str,
        thumbnail: Optional[str],
        download_type: str,
        quality: str,
        output_format: str,
        video_codec: str = "copy",
        sub_lang: Optional[str] = None,
        embed_subs: bool = False,
        cookie_type: str = "none",
        cookie_value: Optional[str] = None,
        proxy: Optional[str] = None,
    ) -> str:
        # Проверяем, нет ли уже точно такой же активной задачи
        for t in self.tasks.values():
            if (t.get("status") in ["queued", "downloading", "processing"] and
                t.get("url") == url and
                t.get("download_type") == download_type and
                t.get("quality") == quality and
                t.get("output_format") == output_format and
                t.get("sub_lang") == sub_lang):
                return t["id"]

        task_id = str(uuid.uuid4())
        task_info = {
            "id": task_id,
            "url": url,
            "title": title or "Загрузка медиа",
            "thumbnail": thumbnail,
            "download_type": download_type,
            "quality": quality,
            "output_format": output_format,
            "video_codec": video_codec,
            "sub_lang": sub_lang,
            "embed_subs": embed_subs,
            "cookie_type": cookie_type,
            "cookie_value": cookie_value,
            "proxy": proxy,
            "status": "queued",
            "percent": 0.0,
            "speed_formatted": "",
            "eta_formatted": "",
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "total_bytes_formatted": "",
            "filename": "",
            "filepath": "",
            "error_message": "",
            "created_at": int(time.time()),
            "completed_at": None,
        }
        self.tasks[task_id] = task_info
        return task_id

    async def start_download_task(self, task_id: str, loop: asyncio.AbstractEventLoop):
        task = self.tasks.get(task_id)
        if not task:
            return

        task["status"] = "downloading"
        await self.broadcast_task_update(task)

        def sync_progress_callback(prog_data: Dict[str, Any]):
            task.update({
                "status": prog_data.get("status", "downloading"),
                "percent": prog_data.get("percent", task.get("percent", 0.0)),
                "speed_formatted": prog_data.get("speed_formatted", ""),
                "eta_formatted": prog_data.get("eta_formatted", ""),
                "downloaded_bytes": prog_data.get("downloaded_bytes", 0),
                "total_bytes": prog_data.get("total_bytes", 0),
                "total_bytes_formatted": prog_data.get("total_bytes_formatted", ""),
                "filename": prog_data.get("filename", task.get("filename", ""))
            })
            try:
                asyncio.run_coroutine_threadsafe(self.broadcast_task_update(task), loop)
            except Exception:
                pass

        try:
            result = await asyncio.to_thread(
                download_media_item,
                url=task["url"],
                download_type=task["download_type"],
                quality=task["quality"],
                output_format=task["output_format"],
                video_codec=task.get("video_codec", "copy"),
                sub_lang=task["sub_lang"],
                embed_subs=task["embed_subs"],
                cookie_type=task["cookie_type"],
                cookie_value=task["cookie_value"],
                proxy=task["proxy"],
                progress_callback=sync_progress_callback
            )

            task.update({
                "status": "completed",
                "percent": 100.0,
                "completed_at": int(time.time()),
                "filename": result["filename"],
                "filepath": result["filepath"],
                "filesize": result["filesize"],
                "filesize_formatted": result["filesize_formatted"],
                "title": result.get("title") or task["title"]
            })

            history_item = {
                "id": task_id,
                "title": task["title"],
                "filename": result["filename"],
                "filepath": result["filepath"],
                "filesize": result["filesize"],
                "filesize_formatted": result["filesize_formatted"],
                "download_type": task["download_type"],
                "output_format": task["output_format"],
                "thumbnail": task["thumbnail"],
                "url": task["url"],
                "completed_at": task["completed_at"]
            }
            self.history.insert(0, history_item)
            self._save_history()

        except Exception as e:
            task.update({
                "status": "error",
                "error_message": str(e),
                "completed_at": int(time.time())
            })
            print(f"Download task {task_id} failed: {e}")

        await self.broadcast_task_update(task)

    async def start_playlist_zip_task(
        self,
        task_id: str,
        items: List[Dict[str, Any]],
        playlist_title: str,
        download_type: str,
        quality: str,
        output_format: str,
        video_codec: str,
        cookie_type: str,
        cookie_value: Optional[str],
        proxy: Optional[str],
        loop: asyncio.AbstractEventLoop
    ):
        """Скачивает все элементы плейлиста и упаковывает их в один ZIP-архив"""
        task = self.tasks.get(task_id)
        if not task:
            return

        task["status"] = "downloading"
        await self.broadcast_task_update(task)

        clean_title = sanitize_filename(playlist_title) or "playlist"
        temp_dir = os.path.join(DOWNLOADS_DIR, f"temp_zip_{task_id[:8]}")
        os.makedirs(temp_dir, exist_ok=True)

        downloaded_files = []
        total_items = len(items)

        try:
            for idx, item in enumerate(items):
                item_url = item.get("url")
                if not item_url:
                    continue

                item_title = item.get("title", f"Track {idx+1}")
                base_pct = (idx / total_items) * 100

                task.update({
                    "title": f"[{idx+1}/{total_items}] {item_title}",
                    "percent": round(base_pct, 1),
                    "status": "downloading"
                })
                await self.broadcast_task_update(task)

                def item_progress_cb(p_data: Dict[str, Any]):
                    item_pct = p_data.get("percent", 0.0)
                    overall_pct = base_pct + (item_pct / total_items)
                    task.update({
                        "percent": round(min(overall_pct, 98.9), 1),
                        "speed_formatted": p_data.get("speed_formatted", ""),
                        "eta_formatted": p_data.get("eta_formatted", ""),
                        "filename": p_data.get("filename", "")
                    })
                    try:
                        asyncio.run_coroutine_threadsafe(self.broadcast_task_update(task), loop)
                    except Exception:
                        pass

                # Скачивание файла
                res = await asyncio.to_thread(
                    download_media_item,
                    url=item_url,
                    download_type=download_type,
                    quality=quality,
                    output_format=output_format,
                    video_codec=video_codec,
                    cookie_type=cookie_type,
                    cookie_value=cookie_value,
                    proxy=proxy,
                    progress_callback=item_progress_cb
                )

                if res.get("filepath") and os.path.exists(res["filepath"]):
                    # Перемещаем файл во временную директорию архива
                    src_fp = res["filepath"]
                    dst_fp = os.path.join(temp_dir, os.path.basename(src_fp))
                    if os.path.exists(dst_fp):
                        try:
                            os.remove(dst_fp)
                        except Exception:
                            pass
                    shutil.move(src_fp, dst_fp)
                    downloaded_files.append(dst_fp)

            # Архивируем все файлы в ZIP
            task.update({
                "status": "processing",
                "percent": 99.0,
                "title": f"Архивация плейлиста '{playlist_title}' в .ZIP...",
                "speed_formatted": "",
                "eta_formatted": "Архивация..."
            })
            await self.broadcast_task_update(task)

            zip_filename = f"[ZIP] {clean_title}.zip"
            zip_filepath = os.path.join(DOWNLOADS_DIR, zip_filename)
            if os.path.exists(zip_filepath):
                zip_filename = f"[ZIP] {clean_title}_{int(time.time())}.zip"
                zip_filepath = os.path.join(DOWNLOADS_DIR, zip_filename)

            def create_zip():
                with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            file_full = os.path.join(root, file)
                            zipf.write(file_full, arcname=file)

            await asyncio.to_thread(create_zip)

            # Очистка временной папки
            shutil.rmtree(temp_dir, ignore_errors=True)

            zip_size = os.path.getsize(zip_filepath) if os.path.exists(zip_filepath) else 0

            task.update({
                "status": "completed",
                "percent": 100.0,
                "completed_at": int(time.time()),
                "title": f"[ZIP] {playlist_title} ({len(downloaded_files)} файлов)",
                "filename": zip_filename,
                "filepath": zip_filepath,
                "filesize": zip_size,
                "filesize_formatted": format_bytes(zip_size),
                "download_type": "zip",
                "output_format": "zip"
            })

            # Добавляем ZIP архив в историю
            history_item = {
                "id": task_id,
                "title": f"📦 [ZIP] {playlist_title} ({len(downloaded_files)} файлов)",
                "filename": zip_filename,
                "filepath": zip_filepath,
                "filesize": zip_size,
                "filesize_formatted": format_bytes(zip_size),
                "download_type": "zip",
                "output_format": "zip",
                "thumbnail": task.get("thumbnail"),
                "url": task.get("url", ""),
                "completed_at": task["completed_at"]
            }
            self.history.insert(0, history_item)
            self._save_history()

        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            task.update({
                "status": "error",
                "error_message": str(e),
                "completed_at": int(time.time())
            })
            print(f"Playlist ZIP task {task_id} failed: {e}")

        await self.broadcast_task_update(task)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(task_id)

    def get_history(self) -> List[Dict[str, Any]]:
        self.history = self._load_history()
        return self.history

    def delete_history_item(self, item_id: str, delete_file: bool = True) -> bool:
        self.history = self._load_history()
        found = None
        for item in self.history:
            if item["id"] == item_id or item.get("filename") == item_id:
                found = item
                break
        if found:
            if delete_file and found.get("filepath") and os.path.exists(found["filepath"]):
                try:
                    os.remove(found["filepath"])
                except Exception:
                    pass
            self.history.remove(found)
            self._save_history()
            return True
        return False

task_manager = TaskManager()
