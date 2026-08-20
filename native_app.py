import os
import sys
import threading
import time
import urllib.request
import io
import re
import tkinter as tk
from tkinter import filedialog, messagebox

# Deno & Bin setup
from backend.path_utils import get_base_dir, get_user_data_dir, get_downloads_dir, get_cookies_dir, get_bin_dir
from backend.ffmpeg_helper import get_ffmpeg_path, get_ffmpeg_version
from backend.cookie_manager import cookie_manager
from backend.downloader import extract_media_info, download_media_item, format_bytes, format_duration

# Ensure Deno is in PATH
for deno_candidate in [
    get_bin_dir(),
    os.path.expanduser("~/.deno/bin"),
    os.path.join(os.environ.get("USERPROFILE", ""), ".deno", "bin"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "deno"),
    "/root/.deno/bin",
    "/usr/local/bin"
]:
    if os.path.isdir(deno_candidate) and deno_candidate not in os.environ.get("PATH", ""):
        os.environ["PATH"] = deno_candidate + os.pathsep + os.environ.get("PATH", "")

import customtkinter as ctk
from PIL import Image, ImageTk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class UniDownloaderNativeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("UniDownloader - Native")
        self.geometry("980x750")
        self.minsize(850, 650)
        self.configure(fg_color="#0d0f18")

        self.extracted_info = None
        self.download_dir = get_downloads_dir()
        self.selected_cookie_file = None
        self.is_downloading = False

        self._build_ui()

    def _build_ui(self):
        # 1. Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="#161926", corner_radius=12)
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        title_label = ctk.CTkLabel(
            header_frame, 
            text="⚡ UniDownloader Native", 
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#ffffff"
        )
        title_label.pack(side="left", padx=20, pady=12)

        status_text = "FFmpeg Ready • 4K/2K Ready"
        status_badge = ctk.CTkLabel(
            header_frame,
            text=status_text,
            font=ctk.CTkFont(size=12),
            text_color="#10b981",
            fg_color="#064e3b",
            corner_radius=8,
            padx=10,
            pady=4
        )
        status_badge.pack(side="right", padx=20, pady=12)

        # 2. Main Scrollable Container
        self.main_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=5)

        # URL Input Card
        url_card = ctk.CTkFrame(self.main_container, fg_color="#161926", corner_radius=12)
        url_card.pack(fill="x", pady=(0, 15), padx=5)

        url_inner = ctk.CTkFrame(url_card, fg_color="transparent")
        url_inner.pack(fill="x", padx=15, pady=15)

        ctk.CTkLabel(
            url_inner, 
            text="Ссылка на медиа:", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#94a3b8"
        ).pack(anchor="w", pady=(0, 6))

        input_row = ctk.CTkFrame(url_inner, fg_color="transparent")
        input_row.pack(fill="x")

        self.url_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Вставьте ссылку на YouTube, TikTok, VK, Instagram, RuTube...",
            font=ctk.CTkFont(size=13),
            height=42,
            fg_color="#0f111a",
            border_color="#334155",
            border_width=1
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda event: self.start_extract())

        paste_btn = ctk.CTkButton(
            input_row,
            text="📋 Вставить",
            width=90,
            height=42,
            fg_color="#334155",
            hover_color="#475569",
            command=self.paste_clipboard
        )
        paste_btn.pack(side="left", padx=(0, 10))

        self.extract_btn = ctk.CTkButton(
            input_row,
            text="🔍 Анализ",
            width=110,
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self.start_extract
        )
        self.extract_btn.pack(side="left")

        # 3. Media Preview & Settings Card (Hidden initially)
        self.media_card = ctk.CTkFrame(self.main_container, fg_color="#161926", corner_radius=12)

        # Thumbnail + Metadata Row
        meta_row = ctk.CTkFrame(self.media_card, fg_color="transparent")
        meta_row.pack(fill="x", padx=15, pady=15)

        self.thumb_label = ctk.CTkLabel(meta_row, text="", width=200, height=115, fg_color="#0b0d14", corner_radius=8)
        self.thumb_label.pack(side="left", padx=(0, 15))

        meta_info = ctk.CTkFrame(meta_row, fg_color="transparent")
        meta_info.pack(side="left", fill="both", expand=True)

        self.title_val = ctk.CTkLabel(
            meta_info, 
            text="Название видео", 
            font=ctk.CTkFont(size=15, weight="bold"),
            wraplength=550,
            justify="left",
            anchor="w"
        )
        self.title_val.pack(anchor="w", pady=(0, 6))

        self.author_val = ctk.CTkLabel(
            meta_info,
            text="Автор: --",
            font=ctk.CTkFont(size=13),
            text_color="#94a3b8",
            anchor="w"
        )
        self.author_val.pack(anchor="w", pady=(0, 3))

        self.duration_val = ctk.CTkLabel(
            meta_info,
            text="Длительность: -- • Просмотры: --",
            font=ctk.CTkFont(size=13),
            text_color="#64748b",
            anchor="w"
        )
        self.duration_val.pack(anchor="w")

        # Divider
        ctk.CTkFrame(self.media_card, height=1, fg_color="#272a38").pack(fill="x", padx=15, pady=5)

        # Options Section
        opts_frame = ctk.CTkFrame(self.media_card, fg_color="transparent")
        opts_frame.pack(fill="x", padx=15, pady=15)

        # Type segmented button (Video / Audio / Subs)
        ctk.CTkLabel(opts_frame, text="Тип скачивания:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#cbd5e1").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.type_switch = ctk.CTkSegmentedButton(
            opts_frame,
            values=["Видео (MP4/MKV)", "Аудио (MP3/FLAC)", "Субтитры"],
            command=self._on_type_change,
            height=35
        )
        self.type_switch.set("Видео (MP4/MKV)")
        self.type_switch.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(0, 8), padx=(10, 0))

        # Resolution dropdown
        self.quality_label = ctk.CTkLabel(opts_frame, text="Разрешение:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#cbd5e1")
        self.quality_label.grid(row=1, column=0, sticky="w", pady=6)

        self.quality_var = ctk.StringVar(value="Максимальное (Best)")
        self.quality_menu = ctk.CTkOptionMenu(
            opts_frame,
            variable=self.quality_var,
            values=["Максимальное (Best)", "1080p Full HD", "720p HD", "480p", "360p"],
            height=35,
            fg_color="#0f111a",
            button_color="#3b82f6",
            button_hover_color="#2563eb"
        )
        self.quality_menu.grid(row=1, column=1, columnspan=2, sticky="ew", pady=6, padx=(10, 0))

        # Codec dropdown
        self.codec_label = ctk.CTkLabel(opts_frame, text="Видеокодек:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#cbd5e1")
        self.codec_label.grid(row=2, column=0, sticky="w", pady=6)

        self.codec_var = ctk.StringVar(value="Исходный (Copy - быстро)")
        self.codec_menu = ctk.CTkOptionMenu(
            opts_frame,
            variable=self.codec_var,
            values=[
                "Исходный (Copy - быстро)",
                "H.264 (AVC - универсальный)",
                "HEVC (H.265 - компактный)",
                "VP9 (Высокое качество)",
                "AV1 (Современный)"
            ],
            height=35,
            fg_color="#0f111a",
            button_color="#334155",
            button_hover_color="#475569"
        )
        self.codec_menu.grid(row=2, column=1, columnspan=2, sticky="ew", pady=6, padx=(10, 0))

        # Container dropdown
        self.format_label = ctk.CTkLabel(opts_frame, text="Контейнер:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#cbd5e1")
        self.format_label.grid(row=3, column=0, sticky="w", pady=6)

        self.format_var = ctk.StringVar(value="mp4")
        self.format_menu = ctk.CTkOptionMenu(
            opts_frame,
            variable=self.format_var,
            values=["mp4", "mkv", "webm", "avi"],
            height=35,
            fg_color="#0f111a",
            button_color="#334155",
            button_hover_color="#475569"
        )
        self.format_menu.grid(row=3, column=1, columnspan=2, sticky="ew", pady=6, padx=(10, 0))

        # Subtitles checkbox
        self.subs_check = ctk.CTkCheckBox(
            opts_frame, 
            text="Вшить субтитры в видео",
            font=ctk.CTkFont(size=13)
        )
        self.subs_check.grid(row=4, column=1, sticky="w", pady=8, padx=(10, 0))

        # Save Directory Row
        ctk.CTkLabel(opts_frame, text="Папка сохранения:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#cbd5e1").grid(row=5, column=0, sticky="w", pady=6)
        
        dir_frame = ctk.CTkFrame(opts_frame, fg_color="transparent")
        dir_frame.grid(row=5, column=1, columnspan=2, sticky="ew", pady=6, padx=(10, 0))

        self.dir_entry = ctk.CTkEntry(
            dir_frame,
            height=35,
            fg_color="#0f111a",
            border_color="#334155",
            border_width=1
        )
        self.dir_entry.insert(0, self.download_dir)
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        choose_dir_btn = ctk.CTkButton(
            dir_frame,
            text="📁 Обзор...",
            width=90,
            height=35,
            fg_color="#334155",
            hover_color="#475569",
            command=self.choose_directory
        )
        choose_dir_btn.pack(side="left")

        opts_frame.columnconfigure(1, weight=1)

        # 4. Download & Live Progress Card
        self.progress_card = ctk.CTkFrame(self.main_container, fg_color="#161926", corner_radius=12)
        self.progress_card.pack(fill="x", pady=(0, 15), padx=5)

        prog_inner = ctk.CTkFrame(self.progress_card, fg_color="transparent")
        prog_inner.pack(fill="x", padx=15, pady=15)

        self.download_btn = ctk.CTkButton(
            prog_inner,
            text="⬇️ СКАЧАТЬ",
            height=46,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=self.start_download
        )
        self.download_btn.pack(fill="x", pady=(0, 12))

        self.progress_bar = ctk.CTkProgressBar(prog_inner, height=12, corner_radius=6, fg_color="#0f111a", progress_color="#3b82f6")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 8))

        prog_details = ctk.CTkFrame(prog_inner, fg_color="transparent")
        prog_details.pack(fill="x")

        self.status_lbl = ctk.CTkLabel(prog_details, text="Готов к скачиванию", font=ctk.CTkFont(size=13), text_color="#94a3b8")
        self.status_lbl.pack(side="left")

        self.speed_lbl = ctk.CTkLabel(prog_details, text="", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8")
        self.speed_lbl.pack(side="right")

        self.open_folder_btn = ctk.CTkButton(
            prog_inner,
            text="📂 Открыть папку со скачанным",
            height=36,
            fg_color="#1e293b",
            hover_color="#334155",
            command=self.open_download_folder
        )

    def paste_clipboard(self):
        try:
            text = self.clipboard_get().strip()
            if text:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, text)
                self.start_extract()
        except Exception:
            pass

    def choose_directory(self):
        folder = filedialog.askdirectory(initialdir=self.download_dir)
        if folder:
            self.download_dir = os.path.abspath(folder)
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, self.download_dir)

    def open_download_folder(self):
        folder = self.dir_entry.get().strip() or self.download_dir
        if os.path.exists(folder):
            os.startfile(folder)

    def _on_type_change(self, value):
        if "Аудио" in value:
            self.quality_label.configure(text="Битрейт:")
            self.quality_menu.configure(values=["MP3 320 kbps (Лучшее)", "MP3 192 kbps (Стандарт)", "MP3 128 kbps", "FLAC (Lossless)", "M4A (AAC)"])
            self.quality_var.set("MP3 320 kbps (Лучшее)")
            self.codec_label.grid_remove()
            self.codec_menu.grid_remove()
            self.format_label.grid_remove()
            self.format_menu.grid_remove()
            self.subs_check.grid_remove()
        elif "Субтитры" in value:
            self.quality_label.configure(text="Язык субтитров:")
            self.quality_menu.configure(values=["Русский (ru)", "Английский (en)", "Все доступные"])
            self.quality_var.set("Русский (ru)")
            self.codec_label.grid_remove()
            self.codec_menu.grid_remove()
            self.format_label.grid_remove()
            self.format_menu.grid_remove()
            self.subs_check.grid_remove()
        else:
            self.quality_label.configure(text="Разрешение:")
            if self.extracted_info and self.extracted_info.get("video_formats"):
                fmt_vals = [f"{vf.get('label')} ({vf.get('codec')}) • {vf.get('filesize_formatted')}" for vf in self.extracted_info.get("video_formats", [])]
                self.quality_menu.configure(values=["Максимальное (Best)"] + fmt_vals)
            else:
                self.quality_menu.configure(values=["Максимальное (Best)", "1080p Full HD", "720p HD", "480p", "360p"])
            self.quality_var.set("Максимальное (Best)")
            self.codec_label.grid()
            self.codec_menu.grid()
            self.format_label.grid()
            self.format_menu.grid()
            self.subs_check.grid()

    def start_extract(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Предупреждение", "Пожалуйста, введите ссылку на видео!")
            return

        self.extract_btn.configure(state="disabled", text="⏳ Анализ...")
        self.status_lbl.configure(text="Извлечение информации о медиа...")
        self.progress_bar.set(0)

        threading.Thread(target=self._async_extract, args=(url,), daemon=True).start()

    def _async_extract(self, url):
        try:
            info = extract_media_info(url)
            self.after(0, self._on_extract_success, info)
        except Exception as e:
            self.after(0, self._on_extract_error, str(e))

    def _on_extract_success(self, info):
        self.extract_btn.configure(state="normal", text="🔍 Анализ")
        self.extracted_info = info

        # Заполняем метаданные
        self.title_val.configure(text=info.get("title", "Без названия"))
        self.author_val.configure(text=f"Автор / Канал: {info.get('uploader', 'Неизвестно')}")
        duration_fmt = format_duration(info.get("duration"))
        views = info.get("view_count")
        views_str = f"{views:,}".replace(",", " ") if views else "--"
        self.duration_val.configure(text=f"Длительность: {duration_fmt} • Просмотры: {views_str}")

        # Формируем список форматов
        video_fmts = info.get("video_formats", [])
        if video_fmts:
            fmt_options = ["Максимальное (Best)"]
            for vf in video_fmts:
                lbl = vf.get("label", "")
                codec = vf.get("codec", "")
                size = vf.get("filesize_formatted", "")
                fmt_options.append(f"{lbl} ({codec}) • {size}")
            self.quality_menu.configure(values=fmt_options)
            self.quality_var.set(fmt_options[0])

        # Загружаем превью
        thumb_url = info.get("thumbnail")
        if thumb_url:
            threading.Thread(target=self._async_load_thumb, args=(thumb_url,), daemon=True).start()

        self.media_card.pack(fill="x", pady=(0, 15), padx=5)
        self.status_lbl.configure(text="Информация получена! Выберите качество и нажмите 'Скачать'.")

    def _async_load_thumb(self, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
                pil_img = Image.open(io.BytesIO(data))
                pil_img = pil_img.resize((200, 115), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(200, 115))
                self.after(0, lambda: self.thumb_label.configure(image=ctk_img, text=""))
        except Exception:
            pass

    def _on_extract_error(self, err):
        self.extract_btn.configure(state="normal", text="🔍 Анализ")
        self.status_lbl.configure(text=f"Ошибка анализа: {err[:60]}")
        messagebox.showerror("Ошибка обработки", f"Не удалось извлечь информацию:\n{err}")

    def start_download(self):
        if self.is_downloading:
            return

        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Предупреждение", "Сначала проанализируйте ссылку!")
            return

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⏳ Скачивание...", fg_color="#64748b")
        self.open_folder_btn.pack_forget()

        # Разбор параметров
        raw_type = self.type_switch.get()
        if "Аудио" in raw_type:
            download_type = "audio"
            quality_sel = self.quality_var.get()
            if "320" in quality_sel:
                quality = "320"
            elif "192" in quality_sel:
                quality = "192"
            elif "128" in quality_sel:
                quality = "128"
            else:
                quality = "best"
            output_format = "mp3" if "MP3" in quality_sel else ("flac" if "FLAC" in quality_sel else "m4a")
            video_codec = "copy"
            sub_lang = None
            embed_subs = False
        elif "Субтитры" in raw_type:
            download_type = "subtitle"
            quality = "best"
            output_format = "srt"
            video_codec = "copy"
            sub_lang = "ru" if "Русский" in self.quality_var.get() else ("en" if "Английский" in self.quality_var.get() else "all")
            embed_subs = False
        else:
            download_type = "video"
            quality_sel = self.quality_var.get()
            if "(" in quality_sel:
                quality = quality_sel.split(" ")[0].replace("p", "")
            else:
                quality = "best"
            output_format = self.format_var.get()
            codec_sel = self.codec_var.get()
            if "H.264" in codec_sel:
                video_codec = "h264"
            elif "HEVC" in codec_sel:
                video_codec = "hevc"
            elif "VP9" in codec_sel:
                video_codec = "vp9"
            elif "AV1" in codec_sel:
                video_codec = "av1"
            else:
                video_codec = "copy"
            sub_lang = "ru"
            embed_subs = bool(self.subs_check.get())

        threading.Thread(
            target=self._async_download,
            args=(url, download_type, quality, output_format, video_codec, sub_lang, embed_subs),
            daemon=True
        ).start()

    def _async_download(self, url, download_type, quality, output_format, video_codec, sub_lang, embed_subs):
        def progress_cb(task_id, progress_data):
            self.after(0, self._on_progress_update, progress_data)

        try:
            # Обновляем целевую папку
            target_dir = self.dir_entry.get().strip() or self.download_dir
            import backend.downloader
            backend.downloader.DOWNLOADS_DIR = target_dir

            res = download_media_item(
                task_id="native_task",
                url=url,
                download_type=download_type,
                quality=quality,
                output_format=output_format,
                video_codec=video_codec,
                sub_lang=sub_lang,
                embed_subs=embed_subs,
                cookie_type="none",
                cookie_value=None,
                proxy=None,
                progress_callback=progress_cb
            )
            self.after(0, self._on_download_complete, res)
        except Exception as e:
            self.after(0, self._on_download_error, str(e))

    def _on_progress_update(self, data):
        pct = (data.get("percent") or 0.0) / 100.0
        self.progress_bar.set(pct)
        speed = data.get("speed_formatted", "")
        eta = data.get("eta_formatted", "")
        speed_text = f"{speed}  {('• ' + eta) if eta else ''}"
        self.speed_lbl.configure(text=speed_text)

        status = data.get("status", "")
        if status == "downloading":
            downloaded = format_bytes(data.get("downloaded_bytes"))
            total = data.get("total_bytes_formatted") or "--"
            self.status_lbl.configure(text=f"Скачивание: {int(pct*100)}% ({downloaded} / {total})")
        elif status == "finished":
            self.status_lbl.configure(text="Обработка и сшивание через FFmpeg...")

    def _on_download_complete(self, res):
        self.is_downloading = False
        self.progress_bar.set(1.0)
        self.download_btn.configure(state="normal", text="⬇️ СКАЧАТЬ ЕЩЁ", fg_color="#10b981")
        self.status_lbl.configure(text="✅ Файл успешно скачан!")
        self.speed_lbl.configure(text="")
        self.open_folder_btn.pack(fill="x", pady=(8, 0))

    def _on_download_error(self, err):
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⬇️ СКАЧАТЬ", fg_color="#10b981")
        self.status_lbl.configure(text="❌ Ошибка при скачивании")
        messagebox.showerror("Ошибка скачивания", f"Не удалось скачать файл:\n{err}")

if __name__ == "__main__":
    app = UniDownloaderNativeApp()
    app.mainloop()
