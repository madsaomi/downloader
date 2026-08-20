# 🤖 AGENTS & AI QUICKSTART GUIDE (UniDownloader)

> **Для ИИ-агентов (Antigravity, Claude, GPT, Cursor, Cline и др.)**:
> Этот файл предназначен для мгновенного понимания структуры и логики проекта без лишних поисковых запросов и траты токенов.

---

## 📌 Краткая сводка проекта

- **Назначение**: Веб-приложение для скачивания видео, аудио, плейлистов, Shorts и субтитров с YouTube, TikTok, VK, Instagram и 1000+ сервисов в максимальном качестве (до 4K/8K, MP3 320k, FLAC, субтитры).
- **Стек**: Python 3.12 + FastAPI + Uvicorn + `yt-dlp` + FFmpeg 7.1 + Vanilla JS / CSS Glassmorphism + WebSockets.
- **ОС**: Windows (x64) и кросс-платформенность.
- **Команда запуска**: `.venv\Scripts\python.exe -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend --reload-dir static`

---

## 🗂 Карта файлов и ответственности

| Файл / Папка | Назначение |
|---|---|
| [`backend/app.py`](file:///c:/Users/~/Desktop/Новая%20папка/backend/app.py) | Главное FastAPI приложение, маршруты REST API, статика и WebSocket `/ws/tasks` |
| [`backend/downloader.py`](file:///c:/Users/~/Desktop/Новая%20папка/backend/downloader.py) | Ядро `yt-dlp` + FFmpeg: `extract_media_info`, `download_media_item`, кодеки |
| [`backend/task_manager.py`](file:///c:/Users/~/Desktop/Новая%20папка/backend/task_manager.py) | Очередь фоновых задач, трансляция прогресса по WebSocket, история |
| [`backend/ffmpeg_helper.py`](file:///c:/Users/~/Desktop/Новая%20папка/backend/ffmpeg_helper.py) | Авто-обнаружение и предоставление пути к `bin/ffmpeg.exe` |
| [`backend/cookie_manager.py`](file:///c:/Users/~/Desktop/Новая%20папка/backend/cookie_manager.py) | Управление профилями cookies (файлы, текст, браузеры) |
| [`static/index.html`](file:///c:/Users/~/Desktop/Новая%20папка/static/index.html) | Разметка SPA, модальные окна, вкладки форматов, плеер |
| [`static/css/style.css`](file:///c:/Users/~/Desktop/Новая%20папка/static/css/style.css) | Glassmorphism дизайн-система, анимации, темы |
| [`static/js/app.js`](file:///c:/Users/~/Desktop/Новая%20папка/static/js/app.js) | Клиентская логика, реактивность, WebSocket, дебаунс, плеер |
| [`downloads/`](file:///c:/Users/~/Desktop/Новая%20папка/downloads) | Директория для сохранения готовых файлов |
| [`cookies/`](file:///c:/Users/~/Desktop/Новая%20папка/cookies) | Директория для сохранения файлов куки |
| [`start.bat`](file:///c:/Users/~/Desktop/Новая%20папка/start.bat) | Скрипт запуска для Windows |

---

## 📚 Подробная документация в папке `.agents/`

Для детальной информации сразу переходите к нужным файлам:
- [`.agents/FAST_CONTEXT.json`](file:///c:/Users/~/Desktop/Новая%20папка/.agents/FAST_CONTEXT.json) — Машиночитаемый JSON-манифест для быстрого контекста.
- [`.agents/ARCHITECTURE.md`](file:///c:/Users/~/Desktop/Новая%20папка/.agents/ARCHITECTURE.md) — Архитектура, потоки данных, многопоточность.
- [`.agents/API_SPECIFICATION.md`](file:///c:/Users/~/Desktop/Новая%20папка/.agents/API_SPECIFICATION.md) — Полная спецификация REST и WebSocket API.
- [`.agents/DEVELOPER_RULES.md`](file:///c:/Users/~/Desktop/Новая%20папка/.agents/DEVELOPER_RULES.md) — Критические правила модификации кода (Windows-совместимость, блокировки дескрипторов, FFmpeg).
