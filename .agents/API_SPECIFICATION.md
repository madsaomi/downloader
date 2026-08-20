# 📡 Спецификация API (API Specification & Protocol)

Полный справочник REST API эндпоинтов и протокола WebSocket.

---

## 1. REST API

### 🔹 `POST /api/extract`
Извлечение метаданных о ссылке (видео или плейлист).

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "cookie_type": "none",        // "none" | "file" | "browser"
  "cookie_value": null,         // "chrome" | "edge" | profile_id
  "proxy": null,                // "http://..." | "socks5://..."
  "is_playlist": false          // true для парсинга как плейлист/канал
}
```

**Response:**
```json
{
  "is_playlist": false,
  "id": "videoId",
  "title": "Название видео",
  "description": "Описание...",
  "duration": 180,
  "duration_formatted": "3:00",
  "thumbnail": "https://...",
  "uploader": "Канал",
  "video_formats": [
    {
      "format_id": "137",
      "height": 1080,
      "width": 1920,
      "fps": 60,
      "ext": "mp4",
      "label": "1080p60",
      "codec": "H.264 (AVC)",
      "filesize": 45000000,
      "filesize_formatted": "42.9 МБ"
    }
  ],
  "audio_formats": [...],
  "subtitles": [
    {
      "code": "ru",
      "name": "Русский",
      "is_auto": false,
      "formats": ["srt", "vtt"]
    }
  ]
}
```

---

### 🔹 `POST /api/download`
Запуск асинхронной задачи скачивания.

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=...",
  "title": "Название видео",
  "thumbnail": "https://...",
  "download_type": "video",       // "video" | "audio" | "subtitle"
  "quality": "best",              // "best" | "1080p" | "720p" | "mp3_320" | "custom_137"
  "output_format": "mp4",         // "mp4" | "mkv" | "webm" | "mp3" | "m4a" | "flac" | "wav" | "srt"
  "video_codec": "copy",          // "copy" | "h264" | "hevc" | "vp9" | "av1" | "h264_recode"
  "sub_lang": "ru",               // опционально для субтитров
  "embed_subs": false,            // вшить субтитры в видео
  "cookie_type": "none",
  "cookie_value": null,
  "proxy": null
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "uuid-v4-string",
  "status": "queued"
}
```

---

### 🔹 `POST /api/batch-download`
Пакетное скачивание массива ссылок отдельными файлами.

**Request Body:**
```json
{
  "items": [
    { "url": "https://...", "title": "Видео 1" },
    { "url": "https://...", "title": "Видео 2" }
  ],
  "download_type": "video",
  "quality": "1080p",
  "output_format": "mp4",
  "video_codec": "copy",
  "cookie_type": "none",
  "cookie_value": null,
  "proxy": null
}
```

---

### 🔹 `POST /api/playlist/download-zip`
Скачивание всех выбранных треков/видео из плейлиста с автоматической упаковкой в единый `.zip` архив.

**Request Body:**
```json
{
  "title": "Название плейлиста",
  "items": [
    { "url": "https://...", "title": "Трек 1" },
    { "url": "https://...", "title": "Трек 2" }
  ],
  "download_type": "audio",       // "audio" | "video"
  "quality": "mp3_320",
  "output_format": "mp3",
  "video_codec": "copy",
  "cookie_type": "none",
  "cookie_value": null,
  "proxy": null
}
```

---

### 🔹 `GET /api/history`
Получение списка скачанных файлов.

---

### 🔹 `DELETE /api/history/{item_id}`
Удаление файла с диска и из истории.

---

### 🔹 `GET /api/download-file/{file_id}`
Скачивание или потоковое воспроизведение (`?inline=true`) файла.

---

### 🔹 `GET /api/cookies`
Список сохраненных файлов куки и поддерживаемых браузеров.

---

### 🔹 `POST /api/cookies/upload` & `POST /api/cookies/save-text`
Загрузка файла `.txt` или сохранение текста куки в Netscape формате.

---

### 🔹 `GET /api/system-info`
Информация о FFmpeg, версии yt-dlp, свободном месте на диске.

---

## 2. WebSocket Протокол (`/ws/tasks`)

Клиент подключается к `ws://localhost:8000/ws/tasks`. Сервер автоматически рассылает сообщения:

**Формат события обновления задачи (`task_update`):**
```json
{
  "type": "task_update",
  "task": {
    "id": "task-uuid",
    "title": "Название видео",
    "status": "downloading",       // "queued" | "downloading" | "processing" | "completed" | "error"
    "percent": 45.8,
    "speed_formatted": "4.2 МБ/с",
    "eta_formatted": "15 сек",
    "downloaded_bytes": 45000000,
    "total_bytes": 98000000,
    "total_bytes_formatted": "93.4 МБ",
    "filename": "Video [id].mp4",
    "error_message": ""
  }
}
```
