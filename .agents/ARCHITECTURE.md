# 🏛 Архитектура UniDownloader (Architecture & Data Flow)

Данный документ описывает внутреннее устройство проекта, жизненный цикл запросов и взаимодействие компонентов.

---

## 1. Схема взаимодействия компонентов

```
[Пользовательский браузер (SPA)]
      │
      ├── (1) HTTP POST /api/extract ──> [backend/app.py] ──> [backend/downloader.py] ──> [yt-dlp extract_info]
      │                                                                                         │
      │   <── (2) JSON (форматы, кодеки, субтитры, превью, плейлист) <────────────────────────┘
      │
      ├── (3) HTTP POST /api/download ──> [backend/app.py] ──> [backend/task_manager.py]
      │                                                               │
      │                                                               └──> Запуск async worker в asyncio.to_thread
      │                                                                           │
      │   <── (4) WebSocket /ws/tasks (Живой прогресс: %, MB/s, ETA) <───────────┤
      │                                                                           ▼
      │                                                                 [backend/downloader.py]
      │                                                                           │
      │                                                                           ├── [yt-dlp core stream download]
      │                                                                           └── [FFmpeg 7.1 merging / recode]
      │                                                                                   │
      │                                                                                   ▼
      │   <── (5) HTTP GET /api/download-file/{id} (Скачивание / Плеер) <───── [downloads/filename.ext]
```

---

## 2. Модули и их ответственность

### 🔹 `backend/app.py`
- Точка входа веб-сервера FastAPI.
- Маршрутизация REST-запросов (`/api/extract`, `/api/download`, `/api/batch-download`, `/api/cookies`, `/api/history`, `/api/system-info`).
- Обработка WebSocket соединения `/ws/tasks` для двусторонней связи и пуш-уведомлений о статусах задач.
- Раздача статических файлов из директории `static/` и безопасная отдача файлов из `downloads/`.

### 🔹 `backend/downloader.py`
- Главная прослойка взаимодействия с библиотекой `yt_dlp.YoutubeDL`.
- Извлекает структурированные метаданные о медиапотоках (разрешение, битрейт, кодеки H.264/AV1/VP9/HEVC, субтитры, хронометраж, элементы плейлиста).
- Запускает загрузку и постпроцессинг:
  - Слияние видео и аудио через FFmpeg в целевой контейнер (MP4, MKV, WebM, MOV, AVI).
  - Извлечение аудио и конвертация в MP3 (320k, 256k, 192k), M4A, FLAC, WAV, OPUS с метаданными и обложкой.
  - Извлечение и конвертация субтитров (SRT, VTT, ASS) или их вшивание внутрь видео.
- Кастомный `progress_hook` с вычислением процентов, скорости и оставшегося времени.

### 🔹 `backend/task_manager.py`
- Хранит состояние всех текущих и завершенных задач (`tasks: Dict[str, Dict]`).
- Отслеживает подключенные WebSocket клиенты и рассылает обновления.
- Реализует защиту от дубликатов задач и файл-рейсов.
- Сохраняет историю успешных загрузок в `downloads/history.json` с проверкой физического присутствия файлов.

### 🔹 `backend/ffmpeg_helper.py`
- Гарантирует наличие рабочего исполняемого файла `ffmpeg.exe` в директории `bin/`.
- Автоматически копирует бинарник из пакета `imageio_ffmpeg` при первом старте.

### 🔹 `backend/cookie_manager.py`
- Управляет хранилищем сессий авторизации (`cookies/profiles.json`).
- Поддерживает интеграцию с опцией `yt-dlp --cookies-from-browser` (Chrome, Edge, Firefox, Brave, Opera, Vivaldi).
- Обеспечивает сохранение файлов `cookies.txt` (Netscape формат) и текстовых сниппетов.

### 🔹 `static/js/app.js` & `static/index.html`
- Одностраничное приложение (SPA) без сборщиков (Webpack/Vite не требуются).
- Прямое управление DOM, реактивное обновление прогресс-баров через WebSocket.
- Встроенный HTML5 видео/аудио плеер для просмотра результатов без скачивания на диск.
- Debounce защита от случайных повторных кликов.
