import os
import re
import time
import math
import asyncio
from typing import Dict, Any, List, Optional, Callable
import yt_dlp

from backend.ffmpeg_helper import get_ffmpeg_path, get_ffmpeg_dir
from backend.cookie_manager import cookie_manager

DOWNLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "downloads"))
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def format_bytes(size: Optional[int]) -> str:
    if size is None or size <= 0:
        return "Неизвестно"
    units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {units[i]}"

def format_duration(seconds: Optional[int]) -> str:
    if not seconds or seconds <= 0:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def build_ydl_options(
    cookie_type: str = "none",
    cookie_value: Optional[str] = None,
    proxy: Optional[str] = None,
    extra_opts: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    ffmpeg_dir = get_ffmpeg_dir()

    opts: Dict[str, Any] = {
        "ffmpeg_location": ffmpeg_dir,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "nocheckcertificate": True,
        "windowsfilenames": True,
        "overwrites": True,
        "updatetime": False,
        "retries": 10,
        "fragment_retries": 10,
        "continuedl": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web", "mweb"]
            }
        }
    }

    if proxy and proxy.strip():
        opts["proxy"] = proxy.strip()

    if cookie_type == "file" and cookie_value:
        cookie_path = cookie_manager.get_cookie_file_path(cookie_value)
        if cookie_path and os.path.exists(cookie_path):
            opts["cookiefile"] = cookie_path
    elif cookie_type == "browser" and cookie_value:
        opts["cookiesfrombrowser"] = (cookie_value.strip().lower(), None, None, None)

    if extra_opts:
        opts.update(extra_opts)

    return opts


def extract_media_info(
    url: str,
    cookie_type: str = "none",
    cookie_value: Optional[str] = None,
    proxy: Optional[str] = None,
    is_playlist: bool = False
) -> Dict[str, Any]:
    """Извлекает полную информацию о видео или плейлисте со всеми кодеками"""
    opts = build_ydl_options(
        cookie_type=cookie_type,
        cookie_value=cookie_value,
        proxy=proxy,
        extra_opts={
            "extract_flat": "in_playlist" if is_playlist else False,
            "skip_download": True,
        }
    )

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            if is_playlist:
                opts["extract_flat"] = False
                with yt_dlp.YoutubeDL(opts) as ydl_retry:
                    info = ydl_retry.extract_info(url, download=False)
            else:
                raise e

    if info is None:
        raise ValueError("Не удалось получить информацию по указанной ссылке")

    # Проверяем, является ли это плейлистом
    if "entries" in info:
        entries = []
        raw_entries = list(info.get("entries") or [])
        for idx, entry in enumerate(raw_entries):
            if not entry:
                continue
            entry_duration = entry.get("duration")
            entries.append({
                "index": idx + 1,
                "id": entry.get("id", str(idx)),
                "title": entry.get("title", f"Видео #{idx+1}"),
                "url": entry.get("url") or entry.get("webpage_url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                "duration": entry_duration,
                "duration_formatted": format_duration(entry_duration),
                "thumbnail": entry.get("thumbnail") or (entry.get("thumbnails", [{}])[-1].get("url") if entry.get("thumbnails") else None),
                "uploader": entry.get("uploader") or entry.get("channel") or info.get("uploader") or "Неизвестно",
                "view_count": entry.get("view_count")
            })

        return {
            "is_playlist": True,
            "id": info.get("id", ""),
            "title": info.get("title", "Плейлист"),
            "uploader": info.get("uploader") or info.get("channel") or "Неизвестно",
            "thumbnail": info.get("thumbnail") or (entries[0]["thumbnail"] if entries else None),
            "webpage_url": info.get("webpage_url", url),
            "entry_count": len(entries),
            "entries": entries,
            "extractor": info.get("extractor_key", "Generic"),
        }

    # Одиночное видео / Shorts / трек
    duration = info.get("duration")
    formats = info.get("formats") or []
    
    video_formats = []
    audio_formats = []
    seen_video_keys = set()
    seen_audio_keys = set()

    for f in formats:
        f_id = f.get("format_id", "")
        ext = f.get("ext", "mp4")
        height = f.get("height")
        width = f.get("width")
        fps = f.get("fps")
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        filesize = f.get("filesize") or f.get("filesize_approx")
        tbr = f.get("tbr")
        abr = f.get("abr")
        vbr = f.get("vbr")

        # Оценка размера
        if not filesize and duration and (tbr or vbr or abr):
            rate = tbr or ((vbr or 0) + (abr or 128))
            filesize = int(rate * 1024 * duration / 8)

        # Определение типа видеокодека
        if vcodec != "none" and height:
            codec_name = "H.264"
            vcodec_lower = vcodec.lower()
            if "avc" in vcodec_lower or "h264" in vcodec_lower:
                codec_name = "H.264 (AVC)"
            elif "av01" in vcodec_lower or "av1" in vcodec_lower:
                codec_name = "AV1"
            elif "vp9" in vcodec_lower or "vp09" in vcodec_lower:
                codec_name = "VP9"
            elif "hevc" in vcodec_lower or "h265" in vcodec_lower or "hvc1" in vcodec_lower:
                codec_name = "H.265 (HEVC)"
            else:
                codec_name = vcodec[:8]

            res_label = f"{height}p"
            if fps and fps > 30:
                res_label += f"{int(fps)}"

            key = (height, fps if fps and fps > 30 else 30, codec_name, ext)
            if key not in seen_video_keys:
                seen_video_keys.add(key)
                video_formats.append({
                    "format_id": f_id,
                    "height": height,
                    "width": width,
                    "fps": fps,
                    "ext": ext,
                    "resolution": f"{width}x{height}" if width and height else f"{height}p",
                    "label": res_label,
                    "codec": codec_name,
                    "raw_vcodec": vcodec,
                    "filesize": filesize,
                    "filesize_formatted": format_bytes(filesize),
                    "has_audio": acodec != "none",
                    "tbr": tbr,
                    "protocol": f.get("protocol", "http")
                })

        # Только аудио поток
        elif vcodec == "none" and acodec != "none":
            audio_bitrate = int(round(abr or tbr or 128))
            codec_label = "AAC" if "mp4a" in acodec or "aac" in acodec else ("Opus" if "opus" in acodec else ("MP3" if "mp3" in acodec else acodec.split(".")[0]))
            
            key = (audio_bitrate, codec_label, ext)
            if key not in seen_audio_keys:
                seen_audio_keys.add(key)
                audio_formats.append({
                    "format_id": f_id,
                    "ext": ext,
                    "abr": audio_bitrate,
                    "codec": codec_label,
                    "raw_acodec": acodec,
                    "filesize": filesize,
                    "filesize_formatted": format_bytes(filesize),
                    "label": f"{audio_bitrate} kbps ({codec_label})"
                })

    video_formats.sort(key=lambda x: (x.get("height") or 0, x.get("fps") or 0, 1 if "H.264" in x.get("codec", "") else 0), reverse=True)
    audio_formats.sort(key=lambda x: (x.get("abr") or 0), reverse=True)

    # Субтитры
    subtitles = []
    manual_subs = info.get("subtitles") or {}
    for lang_code, sub_list in manual_subs.items():
        sub_name = sub_list[0].get("name", lang_code) if sub_list else lang_code
        formats_avail = [s.get("ext", "vtt") for s in sub_list]
        subtitles.append({
            "code": lang_code,
            "name": sub_name,
            "is_auto": False,
            "formats": list(set(formats_avail))
        })

    auto_subs = info.get("automatic_captions") or {}
    for lang_code, sub_list in auto_subs.items():
        if not any(s["code"] == lang_code for s in subtitles):
            sub_name = (sub_list[0].get("name", lang_code) if sub_list else lang_code) + " (Авто)"
            formats_avail = [s.get("ext", "vtt") for s in sub_list]
            subtitles.append({
                "code": lang_code,
                "name": sub_name,
                "is_auto": True,
                "formats": list(set(formats_avail))
            })

    thumbnails = info.get("thumbnails") or []
    best_thumbnail = info.get("thumbnail")
    if thumbnails:
        best_thumbnail = thumbnails[-1].get("url") or best_thumbnail

    return {
        "is_playlist": False,
        "id": info.get("id", ""),
        "title": info.get("title", "Без названия"),
        "description": info.get("description", "")[:400] + ("..." if len(info.get("description", "")) > 400 else ""),
        "duration": duration,
        "duration_formatted": format_duration(duration),
        "thumbnail": best_thumbnail,
        "uploader": info.get("uploader") or info.get("channel") or "Неизвестный автор",
        "uploader_url": info.get("uploader_url") or info.get("channel_url"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "upload_date": info.get("upload_date"),
        "webpage_url": info.get("webpage_url", url),
        "extractor": info.get("extractor_key", "Generic"),
        "is_live": info.get("is_live", False),
        "video_formats": video_formats,
        "audio_formats": audio_formats,
        "subtitles": subtitles
    }


def download_media_item(
    url: str,
    download_type: str,          # "video", "audio", "subtitle"
    quality: str,                # "best", "4320p", "2160p", "1440p", "1080p", "720p", "480p", "360p", or format_id, or "mp3_320", "mp3_256", "mp3_192", "m4a", "flac", "wav", "opus", "ogg", "ac3"
    output_format: str = "mp4",  # mp4, mkv, webm, mov, avi, mp3, m4a, flac, wav, opus, ogg, ac3, srt, vtt
    video_codec: str = "copy",   # "copy", "h264", "hevc", "vp9", "av1"
    sub_lang: Optional[str] = None,
    embed_subs: bool = False,
    cookie_type: str = "none",
    cookie_value: Optional[str] = None,
    proxy: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """Скачивает медиа с поддержкой всех кодеков, контейнеров и надежной защитой от блокировок Windows"""

    ffmpeg_dir = get_ffmpeg_dir()

    # Шаблон имени файла с очисткой
    outtmpl = os.path.join(DOWNLOADS_DIR, "%(title).200B [%(id)s].%(ext)s")

    last_reported_time = 0

    def progress_hook(d):
        nonlocal last_reported_time
        curr_time = time.time()
        if curr_time - last_reported_time < 0.1 and d.get("status") == "downloading":
            return
        last_reported_time = curr_time

        status = d.get("status")
        progress_data = {
            "status": status,
            "filename": os.path.basename(d.get("filename", "")),
            "percent": 0.0,
            "speed": 0,
            "speed_formatted": "0 Б/с",
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "total_bytes_formatted": "",
            "eta": 0,
            "eta_formatted": ""
        }

        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0

            percent = 0.0
            if total > 0:
                percent = round((downloaded / total) * 100, 1)
            elif "_percent_str" in d:
                try:
                    clean_pct = re.sub(r'[^\d.]', '', d["_percent_str"])
                    percent = float(clean_pct)
                except Exception:
                    pass

            progress_data.update({
                "percent": min(percent, 99.9),
                "downloaded_bytes": downloaded,
                "total_bytes": total,
                "total_bytes_formatted": format_bytes(total),
                "speed": speed,
                "speed_formatted": f"{format_bytes(speed)}/с" if speed else "",
                "eta": eta,
                "eta_formatted": f"{int(eta)} сек" if eta else ""
            })

        elif status == "finished":
            progress_data.update({
                "status": "processing",
                "percent": 100.0,
                "message": "Обработка и объединение медиапотоков..."
            })

        if progress_callback:
            progress_callback(progress_data)

    ydl_opts: Dict[str, Any] = {
        "outtmpl": outtmpl,
        "ffmpeg_location": ffmpeg_dir,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "windowsfilenames": True,
        "overwrites": True,
        "updatetime": False,
        "retries": 10,
        "fragment_retries": 10,
        "continuedl": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web", "mweb"]
            }
        }
    }

    if proxy and proxy.strip():
        ydl_opts["proxy"] = proxy.strip()

    if cookie_type == "file" and cookie_value:
        cookie_path = cookie_manager.get_cookie_file_path(cookie_value)
        if cookie_path and os.path.exists(cookie_path):
            ydl_opts["cookiefile"] = cookie_path
    elif cookie_type == "browser" and cookie_value:
        ydl_opts["cookiesfrombrowser"] = (cookie_value.strip().lower(), None, None, None)

    # 1. ТОЛЬКО АУДИО
    if download_type == "audio":
        ydl_opts["format"] = "bestaudio/best"
        target_audio_codec = output_format if output_format in ["mp3", "m4a", "flac", "wav", "opus", "ogg", "ac3", "alac"] else "mp3"
        
        quality_val = "0" # best VBR
        if "320" in quality:
            quality_val = "320"
        elif "256" in quality:
            quality_val = "256"
        elif "192" in quality:
            quality_val = "192"
        elif "128" in quality:
            quality_val = "128"

        postprocessors = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": target_audio_codec,
            "preferredquality": quality_val,
        }, {
            "key": "FFmpegMetadata",
            "add_metadata": True,
        }]

        if target_audio_codec in ["mp3", "m4a", "flac"]:
            ydl_opts["writethumbnail"] = True
            postprocessors.append({"key": "EmbedThumbnail"})

        ydl_opts["postprocessors"] = postprocessors

    # 2. СУБТИТРЫ
    elif download_type == "subtitle":
        ydl_opts["skip_download"] = True
        ydl_opts["writesubtitles"] = True
        ydl_opts["writeautomaticsub"] = True
        if sub_lang:
            ydl_opts["subtitleslangs"] = [sub_lang]
        sub_fmt = output_format if output_format in ["srt", "vtt", "ass", "lrc"] else "srt"
        ydl_opts["subtitlesformat"] = sub_fmt
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegSubtitlesConvertor",
            "format": sub_fmt
        }]

    # 3. ВИДЕО
    else:
        # Выбор видео-потока
        if quality.startswith("custom_"):
            format_id = quality.replace("custom_", "")
            ydl_opts["format"] = f"{format_id}+bestaudio/best"
        elif quality in ["4320p", "2160p", "1440p", "1080p", "720p", "480p", "360p", "240p"]:
            res_num = int(quality.replace("p", ""))
            if video_codec == "h264":
                ydl_opts["format"] = f"bestvideo[height<={res_num}][vcodec^=avc]+bestaudio/bestvideo[height<={res_num}]+bestaudio/best[height<={res_num}]/best"
            else:
                ydl_opts["format"] = f"bestvideo[height<={res_num}]+bestaudio/best[height<={res_num}]/best"
        elif quality == "best":
            if video_codec == "h264":
                ydl_opts["format"] = "bestvideo[vcodec^=avc]+bestaudio/bestvideo+bestaudio/best"
            else:
                ydl_opts["format"] = "bestvideo+bestaudio/best"
        else:
            ydl_opts["format"] = f"{quality}+bestaudio/best" if "+" not in quality else quality

        target_container = output_format if output_format in ["mp4", "mkv", "webm", "mov", "avi", "ts"] else "mp4"
        ydl_opts["merge_output_format"] = target_container

        postprocessors = [{
            "key": "FFmpegMetadata",
            "add_metadata": True,
        }]

        # Если требуется гарантированное перекодирование в H.264
        if video_codec == "h264_recode":
            ydl_opts["postprocessor_args"] = {
                "ffmpeg": ["-c:v", "libx264", "-crf", "21", "-preset", "fast", "-c:a", "aac", "-b:a", "192k"]
            }

        if embed_subs and sub_lang:
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = True
            ydl_opts["subtitleslangs"] = [sub_lang]
            postprocessors.append({
                "key": "FFmpegEmbedSubtitle",
                "already_have_subtitle": False
            })

        ydl_opts["postprocessors"] = postprocessors

    # Запускаем загрузку с обработкой возможных временных блокировок файлов на Windows
    info_dict = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                break
        except Exception as e:
            err_str = str(e)
            if "WinError 32" in err_str or "used by another process" in err_str:
                if attempt < max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
            raise e

    downloaded_filepath = None
    if info_dict:
        if "requested_downloads" in info_dict and info_dict["requested_downloads"]:
            downloaded_filepath = info_dict["requested_downloads"][0].get("filepath")
        if not downloaded_filepath:
            downloaded_filepath = ydl.prepare_filename(info_dict)
            base, _ = os.path.splitext(downloaded_filepath)
            if download_type == "audio":
                downloaded_filepath = f"{base}.{target_audio_codec}"
            elif download_type == "subtitle":
                downloaded_filepath = f"{base}.{output_format}"
            elif target_container:
                downloaded_filepath = f"{base}.{target_container}"

    # Поиск созданного файла
    final_file = downloaded_filepath
    expected_ext = target_audio_codec if download_type == "audio" else (output_format if download_type == "subtitle" else target_container)

    if not final_file or not os.path.exists(final_file) or not final_file.endswith(f".{expected_ext}"):
        base_name = os.path.splitext(os.path.basename(downloaded_filepath or ""))[0]
        candidates = []
        for f in os.listdir(DOWNLOADS_DIR):
            if f.endswith(f".{expected_ext}") and (info_dict.get("id", "___") in f or (base_name and base_name[:20] in f)):
                full_cand = os.path.join(DOWNLOADS_DIR, f)
                try:
                    candidates.append((os.path.getmtime(full_cand), full_cand))
                except Exception:
                    pass
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            final_file = candidates[0][1]

    file_size = os.path.getsize(final_file) if final_file and os.path.exists(final_file) else 0

    return {
        "success": True,
        "title": info_dict.get("title", "") if info_dict else "",
        "filename": os.path.basename(final_file) if final_file else "",
        "filepath": final_file or "",
        "filesize": file_size,
        "filesize_formatted": format_bytes(file_size),
        "duration": info_dict.get("duration") if info_dict else 0,
        "thumbnail": info_dict.get("thumbnail") if info_dict else None,
        "download_type": download_type,
        "output_format": expected_ext
    }
