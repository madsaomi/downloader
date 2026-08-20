# ⚠️ ПРАВИЛА ДЛЯ РАЗРАБОТЧИКОВ И ИИ-АГЕНТОВ (Developer & AI Rules)

Соблюдайте эти правила при любых доработках или рефакторинге проекта, чтобы не сломать функционал на Windows и не вызвать ошибок:

---

## 🚫 1. Никогда не включайте watch на всю директорию в Uvicorn
- **Проблема**: Если Uvicorn отслеживает корень проекта, `WatchFiles` пытается прочесть и заблокировать временные `.part` файлы в папке `downloads/`. Это вызывает `[WinError 32]` в Windows и ломает скачивание!
- **Правило**: Uvicorn ВСЕГДА должен запускаться с явным ограничением директорий:
  ```bash
  --reload --reload-dir backend --reload-dir static
  ```

---

## ⚙️ 2. Правила вызова yt-dlp
При формировании `ydl_opts` в `backend/downloader.py`:
- `ffmpeg_location` ВСЕГДА должен устанавливаться через `get_ffmpeg_dir()` (возвращает путь к `bin/` с `ffmpeg.exe`).
- Обязательно указывать:
  - `"windowsfilenames": True` (экранирует спецсимволы в именах файлов для Windows).
  - `"overwrites": True` (перезаписывает недокачанные файлы при повторе).
  - `"updatetime": False` (не триггерит индексаторы файлов лишними изменениями mtime).
  - `"retries": 10`, `"fragment_retries": 10`.

---

## ⚡ 3. Защита от дубликатов задач и гонок (Race conditions)
- В `backend/task_manager.py` встроена проверка: если задача с идентичными параметрами `(url, download_type, quality, output_format)` уже выполняется, возвращается существующий `task_id` без запуска параллельного дубликата.
- Во фронтенде `static/js/app.js` кнопки скачивания блокируются на 1.5 секунды с анимацией загрузки для предотвращения дабл-клика пользователя.

---

## 🎨 4. Архитектура фронтенда
- Фронтенд работает без Node.js сборки (нет `package.json`, `npm run build` не требуется).
- Все библиотеки загружаются через CDN: Tailwind CSS, Lucide Icons.
- Стили и кастомный Glassmorphism находятся в `static/css/style.css`.
- При добавлении новых HTML-элементов с иконками `data-lucide` обязательно вызывайте `lucide.createIcons()`.

---

## 🧪 5. Проверка изменений
Перед завершением задач проверяйте работоспособность бекенда командой:
```powershell
.venv\Scripts\python.exe -c "import backend.app, backend.downloader, backend.task_manager; print('OK')"
```
