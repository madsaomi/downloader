import os
import sys
import threading
import time
import urllib.request
import io
import re
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

# Deno & Bin setup
from backend.path_utils import get_base_dir, get_user_data_dir, get_downloads_dir, get_cookies_dir, get_bin_dir
from backend.ffmpeg_helper import get_ffmpeg_path, get_ffmpeg_version
from backend.cookie_manager import cookie_manager
from backend.downloader import extract_media_info, download_media_item, format_bytes, format_duration

# Ensure Deno and local bin are in PATH
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
from PIL import Image, ImageTk, ImageDraw

# Modern Dark Theme Palette
THEME = {
    "bg": "#0B0D14",
    "card": "#151824",
    "card_border": "#24293E",
    "card_hover": "#1C2030",
    "input_bg": "#0F111B",
    "input_border": "#2D344B",
    "accent_blue": "#3B82F6",
    "accent_blue_hover": "#2563EB",
    "accent_green": "#10B981",
    "accent_green_hover": "#059669",
    "accent_purple": "#8B5CF6",
    "accent_purple_hover": "#7C3AED",
    "accent_amber": "#F59E0B",
    "text_primary": "#FFFFFF",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    "badge_green_bg": "#064E3B",
    "badge_green_text": "#34D399",
    "badge_blue_bg": "#1E3A8A",
    "badge_blue_text": "#60A5FA",
    "badge_purple_bg": "#4C1D95",
    "badge_purple_text": "#C084FC",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class UniDownloaderNativeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("UniDownloader — Ultimate Media Downloader")
        self.geometry("1020x820")
        self.minsize(900, 700)
        self.configure(fg_color=THEME["bg"])

        self.extracted_info = None
        self.download_dir = get_downloads_dir()
        self.is_downloading = False
        self.last_downloaded_file = None
        self.recent_downloads = []

        self._build_ui()

    def _build_ui(self):
        # 1. Header with Gradient-like Glassmorphism Card
        header_card = ctk.CTkFrame(self, fg_color=THEME["card"], border_color=THEME["card_border"], border_width=1, corner_radius=14)
        header_card.pack(fill="x", padx=24, pady=(18, 12))

        header_inner = ctk.CTkFrame(header_card, fg_color="transparent")
        header_inner.pack(fill="x", padx=20, pady=14)

        # Left Title + Subtitle
        title_box = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_box.pack(side="left")

        app_title = ctk.CTkLabel(
            title_box,
            text="⚡ UniDownloader",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=THEME["text_primary"]
        )
        app_title.pack(anchor="w")

        app_sub = ctk.CTkLabel(
            title_box,
            text="Скачивание 4K, 2K, 1080p, MP3 320k с YouTube, TikTok, VK, Instagram и 1000+ сайтов",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"]
        )
        app_sub.pack(anchor="w", pady=(2, 0))

        # Right Badges
        badges_box = ctk.CTkFrame(header_inner, fg_color="transparent")
        badges_box.pack(side="right")

        badge_4k = ctk.CTkLabel(
            badges_box,
            text="✨ 4K/8K Engine",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["badge_purple_text"],
            fg_color=THEME["badge_purple_bg"],
            corner_radius=8,
            padx=10,
            pady=5
        )
        badge_4k.pack(side="left", padx=4)

        badge_ffmpeg = ctk.CTkLabel(
            badges_box,
            text="🎬 FFmpeg 7.1",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["badge_green_text"],
            fg_color=THEME["badge_green_bg"],
            corner_radius=8,
            padx=10,
            pady=5
        )
        badge_ffmpeg.pack(side="left", padx=4)

        # 2. Main Scrollable View
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # URL Input Card
        url_card = ctk.CTkFrame(self.scroll_frame, fg_color=THEME["card"], border_color=THEME["card_border"], border_width=1, corner_radius=14)
        url_card.pack(fill="x", pady=(0, 14), padx=4)

        url_inner = ctk.CTkFrame(url_card, fg_color="transparent")
        url_inner.pack(fill="x", padx=18, pady=18)

        # URL Label + Platform Icons
        url_top = ctk.CTkFrame(url_inner, fg_color="transparent")
        url_top.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            url_top,
            text="🔗 Вставьте ссылку на видео или плейлист:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"]
        ).pack(side="left")

        ctk.CTkLabel(
            url_top,
            text="YouTube • TikTok • VK • Instagram • RuTube • Twitter",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_muted"]
        ).pack(side="right")

        # Entry Row
        entry_row = ctk.CTkFrame(url_inner, fg_color="transparent")
        entry_row.pack(fill="x")

        self.url_entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="https://www.youtube.com/watch?v=... или любая ссылка",
            font=ctk.CTkFont(size=14),
            height=46,
            fg_color=THEME["input_bg"],
            border_color=THEME["input_border"],
            border_width=1.5,
            corner_radius=10
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda event: self.start_extract())

        paste_btn = ctk.CTkButton(
            entry_row,
            text="📋 Вставить",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=100,
            height=46,
            fg_color="#262C40",
            hover_color="#343C56",
            corner_radius=10,
            command=self.paste_clipboard
        )
        paste_btn.pack(side="left", padx=(0, 10))

        self.extract_btn = ctk.CTkButton(
            entry_row,
            text="🔍 Анализ",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=120,
            height=46,
            fg_color=THEME["accent_blue"],
            hover_color=THEME["accent_blue_hover"],
            corner_radius=10,
            command=self.start_extract
        )
        self.extract_btn.pack(side="left")

        # Quick 1-Click Preset Buttons Row
        preset_row = ctk.CTkFrame(url_inner, fg_color="transparent")
        preset_row.pack(fill="x", pady=(12, 0))

        ctk.CTkLabel(preset_row, text="Быстрый выбор:", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_muted"]).pack(side="left", padx=(0, 8))

        presets = [
            ("⭐ 4K / 2K Макс", lambda: self._apply_preset("4k")),
            ("🎬 Full HD 1080p", lambda: self._apply_preset("1080p")),
            ("📱 HD 720p", lambda: self._apply_preset("720p")),
            ("🎵 MP3 320 kbps", lambda: self._apply_preset("mp3")),
        ]
        for title, cmd in presets:
            btn = ctk.CTkButton(
                preset_row,
                text=title,
                font=ctk.CTkFont(size=12),
                height=30,
                fg_color="#1F2436",
                hover_color="#2D344B",
                border_color="#333D5E",
                border_width=1,
                corner_radius=8,
                command=cmd
            )
            btn.pack(side="left", padx=4)

        # 3. Media Preview & Settings Card
        self.media_card = ctk.CTkFrame(self.scroll_frame, fg_color=THEME["card"], border_color=THEME["card_border"], border_width=1, corner_radius=14)

        # Metadata Header Frame
        meta_row = ctk.CTkFrame(self.media_card, fg_color="transparent")
        meta_row.pack(fill="x", padx=18, pady=18)

        # Thumbnail Image Label
        self.thumb_label = ctk.CTkLabel(
            meta_row, 
            text="Превью видео", 
            width=220, 
            height=125, 
            fg_color="#090B12", 
            corner_radius=10
        )
        self.thumb_label.pack(side="left", padx=(0, 18))

        # Title & Info Labels
        meta_info = ctk.CTkFrame(meta_row, fg_color="transparent")
        meta_info.pack(side="left", fill="both", expand=True)

        self.title_val = ctk.CTkLabel(
            meta_info,
            text="Название видео",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=THEME["text_primary"],
            wraplength=600,
            justify="left",
            anchor="w"
        )
        self.title_val.pack(anchor="w", pady=(0, 6))

        self.author_val = ctk.CTkLabel(
            meta_info,
            text="👤 Автор: --",
            font=ctk.CTkFont(size=13),
            text_color=THEME["text_secondary"],
            anchor="w"
        )
        self.author_val.pack(anchor="w", pady=(0, 4))

        self.duration_val = ctk.CTkLabel(
            meta_info,
            text="⏱ Длительность: -- • 👁 Просмотры: --",
            font=ctk.CTkFont(size=13),
            text_color=THEME["text_muted"],
            anchor="w"
        )
        self.duration_val.pack(anchor="w")

        # Divider
        ctk.CTkFrame(self.media_card, height=1, fg_color=THEME["card_border"]).pack(fill="x", padx=18, pady=4)

        # Options Settings Grid
        opts_grid = ctk.CTkFrame(self.media_card, fg_color="transparent")
        opts_grid.pack(fill="x", padx=18, pady=16)

        # Type segmented button
        ctk.CTkLabel(opts_grid, text="Тип формата:", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_secondary"]).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.type_switch = ctk.CTkSegmentedButton(
            opts_grid,
            values=["🎬 Видео (MP4 / MKV)", "🎵 Аудио (MP3 / FLAC)", "📝 Субтитры"],
            command=self._on_type_change,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            selected_color=THEME["accent_blue"],
            selected_hover_color=THEME["accent_blue_hover"],
            corner_radius=10
        )
        self.type_switch.set("🎬 Видео (MP4 / MKV)")
        self.type_switch.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(0, 10), padx=(12, 0))

        # Resolution Dropdown
        self.quality_label = ctk.CTkLabel(opts_grid, text="Качество / Формат:", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_secondary"])
        self.quality_label.grid(row=1, column=0, sticky="w", pady=7)

        self.quality_var = ctk.StringVar(value="⭐ Максимальное (4K / 2K / 1080p)")
        self.quality_menu = ctk.CTkOptionMenu(
            opts_grid,
            variable=self.quality_var,
            values=["⭐ Максимальное (4K / 2K / 1080p)", "🎬 1080p Full HD (MP4)", "📱 720p HD (MP4)", "480p", "360p"],
            height=38,
            font=ctk.CTkFont(size=13),
            fg_color=THEME["input_bg"],
            button_color=THEME["accent_blue"],
            button_hover_color=THEME["accent_blue_hover"],
            corner_radius=10
        )
        self.quality_menu.grid(row=1, column=1, columnspan=2, sticky="ew", pady=7, padx=(12, 0))

        # Video Codec Dropdown
        self.codec_label = ctk.CTkLabel(opts_grid, text="Видеокодек:", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_secondary"])
        self.codec_label.grid(row=2, column=0, sticky="w", pady=7)

        self.codec_var = ctk.StringVar(value="Исходный (Copy — мгновенно)")
        self.codec_menu = ctk.CTkOptionMenu(
            opts_grid,
            variable=self.codec_var,
            values=[
                "Исходный (Copy — мгновенно)",
                "H.264 (AVC — совместим со всеми ТВ и смартфонами)",
                "HEVC (H.265 — высокое сжатие)",
                "VP9 (Высокое качество YouTube)",
                "AV1 (Современный ультра-кодек)"
            ],
            height=38,
            font=ctk.CTkFont(size=13),
            fg_color=THEME["input_bg"],
            button_color="#262C40",
            button_hover_color="#343C56",
            corner_radius=10
        )
        self.codec_menu.grid(row=2, column=1, columnspan=2, sticky="ew", pady=7, padx=(12, 0))

        # Container format Dropdown
        self.format_label = ctk.CTkLabel(opts_grid, text="Контейнер:", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_secondary"])
        self.format_label.grid(row=3, column=0, sticky="w", pady=7)

        self.format_var = ctk.StringVar(value="mp4")
        self.format_menu = ctk.CTkOptionMenu(
            opts_grid,
            variable=self.format_var,
            values=["mp4", "mkv", "webm", "avi"],
            height=38,
            font=ctk.CTkFont(size=13),
            fg_color=THEME["input_bg"],
            button_color="#262C40",
            button_hover_color="#343C56",
            corner_radius=10
        )
        self.format_menu.grid(row=3, column=1, columnspan=2, sticky="ew", pady=7, padx=(12, 0))

        # Subtitles checkbox
        self.subs_check = ctk.CTkCheckBox(
            opts_grid,
            text="Вшить русские субтитры в видеофайл",
            font=ctk.CTkFont(size=13),
            fg_color=THEME["accent_blue"],
            hover_color=THEME["accent_blue_hover"]
        )
        self.subs_check.grid(row=4, column=1, sticky="w", pady=9, padx=(12, 0))

        # Save Directory Row
        ctk.CTkLabel(opts_grid, text="Куда сохранить:", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_secondary"]).grid(row=5, column=0, sticky="w", pady=7)

        dir_frame = ctk.CTkFrame(opts_grid, fg_color="transparent")
        dir_frame.grid(row=5, column=1, columnspan=2, sticky="ew", pady=7, padx=(12, 0))

        self.dir_entry = ctk.CTkEntry(
            dir_frame,
            height=38,
            font=ctk.CTkFont(size=13),
            fg_color=THEME["input_bg"],
            border_color=THEME["input_border"],
            border_width=1,
            corner_radius=10
        )
        self.dir_entry.insert(0, self.download_dir)
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        choose_dir_btn = ctk.CTkButton(
            dir_frame,
            text="📁 Обзор...",
            width=95,
            height=38,
            font=ctk.CTkFont(size=13),
            fg_color="#262C40",
            hover_color="#343C56",
            corner_radius=10,
            command=self.choose_directory
        )
        choose_dir_btn.pack(side="left")

        opts_grid.columnconfigure(1, weight=1)

        # 4. Download & Live Progress Card
        self.progress_card = ctk.CTkFrame(self.scroll_frame, fg_color=THEME["card"], border_color=THEME["card_border"], border_width=1, corner_radius=14)
        self.progress_card.pack(fill="x", pady=(0, 14), padx=4)

        prog_inner = ctk.CTkFrame(self.progress_card, fg_color="transparent")
        prog_inner.pack(fill="x", padx=18, pady=18)

        self.download_btn = ctk.CTkButton(
            prog_inner,
            text="⬇️ СКАЧАТЬ В МАКСИМАЛЬНОМ КАЧЕСТВЕ",
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=THEME["accent_green"],
            hover_color=THEME["accent_green_hover"],
            corner_radius=12,
            command=self.start_download
        )
        self.download_btn.pack(fill="x", pady=(0, 14))

        # Progress Bar with glow color
        self.progress_bar = ctk.CTkProgressBar(
            prog_inner,
            height=14,
            corner_radius=7,
            fg_color="#090B12",
            progress_color=THEME["accent_blue"]
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 10))

        # Live Info Row
        prog_details = ctk.CTkFrame(prog_inner, fg_color="transparent")
        prog_details.pack(fill="x")

        self.status_lbl = ctk.CTkLabel(
            prog_details,
            text="Готов к работе. Вставьте ссылку для начала.",
            font=ctk.CTkFont(size=13),
            text_color=THEME["text_secondary"]
        )
        self.status_lbl.pack(side="left")

        self.speed_lbl = ctk.CTkLabel(
            prog_details,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38BDF8"
        )
        self.speed_lbl.pack(side="right")

        # Finished Action Buttons Row
        self.finish_actions = ctk.CTkFrame(prog_inner, fg_color="transparent")

        self.open_folder_btn = ctk.CTkButton(
            self.finish_actions,
            text="📂 Показать файл в папке",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            fg_color="#1E293B",
            hover_color="#334155",
            corner_radius=10,
            command=self.open_download_folder
        )
        self.open_folder_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.play_file_btn = ctk.CTkButton(
            self.finish_actions,
            text="▶️ Воспроизвести",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            fg_color=THEME["accent_purple"],
            hover_color=THEME["accent_purple_hover"],
            corner_radius=10,
            command=self.play_downloaded_file
        )
        self.play_file_btn.pack(side="left", fill="x", expand=True)

    def paste_clipboard(self):
        try:
            text = self.clipboard_get().strip()
            if text:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, text)
                self.start_extract()
        except Exception:
            pass

    def _apply_preset(self, preset_type):
        if preset_type == "4k":
            self.type_switch.set("🎬 Видео (MP4 / MKV)")
            self._on_type_change("Видео")
            self.quality_var.set("⭐ Максимальное (4K / 2K / 1080p)")
            self.codec_var.set("Исходный (Copy — мгновенно)")
            self.format_var.set("mp4")
        elif preset_type == "1080p":
            self.type_switch.set("🎬 Видео (MP4 / MKV)")
            self._on_type_change("Видео")
            # find 1080p in options
            vals = self.quality_menu.cget("values")
            matching = [v for v in vals if "1080p" in v]
            self.quality_var.set(matching[0] if matching else "🎬 1080p Full HD (MP4)")
            self.codec_var.set("H.264 (AVC — совместим со всеми ТВ и смартфонами)")
            self.format_var.set("mp4")
        elif preset_type == "720p":
            self.type_switch.set("🎬 Видео (MP4 / MKV)")
            self._on_type_change("Видео")
            vals = self.quality_menu.cget("values")
            matching = [v for v in vals if "720p" in v]
            self.quality_var.set(matching[0] if matching else "📱 720p HD (MP4)")
            self.codec_var.set("H.264 (AVC — совместим со всеми ТВ и смартфонами)")
            self.format_var.set("mp4")
        elif preset_type == "mp3":
            self.type_switch.set("🎵 Аудио (MP3 / FLAC)")
            self._on_type_change("Аудио")
            self.quality_var.set("MP3 320 kbps (Максимальное качество)")

        if self.url_entry.get().strip() and self.extracted_info:
            self.start_download()
        elif self.url_entry.get().strip():
            self.start_extract()

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

    def play_downloaded_file(self):
        if self.last_downloaded_file and os.path.exists(self.last_downloaded_file):
            os.startfile(self.last_downloaded_file)
        else:
            self.open_download_folder()

    def _on_type_change(self, value):
        if "Аудио" in value:
            self.quality_label.configure(text="Битрейт аудио:")
            self.quality_menu.configure(values=[
                "MP3 320 kbps (Максимальное качество)",
                "MP3 192 kbps (Оптимальный баланс)",
                "MP3 128 kbps (Компактный размер)",
                "FLAC (Lossless — без потери качества)",
                "M4A (AAC — оригинальный звук)"
            ])
            self.quality_var.set("MP3 320 kbps (Максимальное качество)")
            self.codec_label.grid_remove()
            self.codec_menu.grid_remove()
            self.format_label.grid_remove()
            self.format_menu.grid_remove()
            self.subs_check.grid_remove()
        elif "Субтитры" in value:
            self.quality_label.configure(text="Язык субтитров:")
            self.quality_menu.configure(values=["Русский (ru)", "Английский (en)", "Все доступные языки"])
            self.quality_var.set("Русский (ru)")
            self.codec_label.grid_remove()
            self.codec_menu.grid_remove()
            self.format_label.grid_remove()
            self.format_menu.grid_remove()
            self.subs_check.grid_remove()
        else:
            self.quality_label.configure(text="Качество / Формат:")
            if self.extracted_info and self.extracted_info.get("video_formats"):
                fmt_vals = ["⭐ Максимальное (4K / 2K / 1080p)"]
                for vf in self.extracted_info.get("video_formats", []):
                    lbl = vf.get("label", "")
                    codec = vf.get("codec", "")
                    size = vf.get("filesize_formatted", "")
                    fmt_vals.append(f"{lbl} ({codec}) • {size}")
                self.quality_menu.configure(values=fmt_vals)
                self.quality_var.set(fmt_vals[0])
            else:
                self.quality_menu.configure(values=["⭐ Максимальное (4K / 2K / 1080p)", "🎬 1080p Full HD (MP4)", "📱 720p HD (MP4)", "480p", "360p"])
                self.quality_var.set("⭐ Максимальное (4K / 2K / 1080p)")
            self.codec_label.grid()
            self.codec_menu.grid()
            self.format_label.grid()
            self.format_menu.grid()
            self.subs_check.grid()

    def start_extract(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Внимание", "Пожалуйста, вставьте ссылку на видео или аудио!")
            return

        self.extract_btn.configure(state="disabled", text="⏳ Анализ...")
        self.status_lbl.configure(text="🔍 Получение списка форматов и информации...")
        self.progress_bar.set(0)
        self.finish_actions.pack_forget()

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

        # Fill Metadata
        title = info.get("title", "Без названия")
        self.title_val.configure(text=title)
        self.author_val.configure(text=f"👤 Автор: {info.get('uploader', 'Неизвестно')}")
        
        duration_fmt = format_duration(info.get("duration"))
        views = info.get("view_count")
        views_str = f"{views:,}".replace(",", " ") if views else "--"
        self.duration_val.configure(text=f"⏱ Длительность: {duration_fmt}  •  👁 Просмотры: {views_str}")

        # Update Formats List
        video_fmts = info.get("video_formats", [])
        if video_fmts:
            fmt_options = ["⭐ Максимальное (4K / 2K / 1080p)"]
            for vf in video_fmts:
                lbl = vf.get("label", "")
                codec = vf.get("codec", "")
                size = vf.get("filesize_formatted", "")
                fmt_options.append(f"{lbl} ({codec}) • {size}")
            self.quality_menu.configure(values=fmt_options)
            self.quality_var.set(fmt_options[0])

        # Load Thumbnail
        thumb_url = info.get("thumbnail")
        if thumb_url:
            threading.Thread(target=self._async_load_thumb, args=(thumb_url,), daemon=True).start()

        self.media_card.pack(fill="x", pady=(0, 14), padx=4)
        self.status_lbl.configure(text="✅ Информация получена! Выберите качество и нажмите 'Скачать'.")

    def _async_load_thumb(self, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
                pil_img = Image.open(io.BytesIO(data))
                pil_img = pil_img.resize((220, 125), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(220, 125))
                self.after(0, lambda: self.thumb_label.configure(image=ctk_img, text=""))
        except Exception:
            pass

    def _on_extract_error(self, err):
        self.extract_btn.configure(state="normal", text="🔍 Анализ")
        self.status_lbl.configure(text=f"❌ Ошибка: {err[:60]}")
        messagebox.showerror("Ошибка обработки", f"Не удалось извлечь информацию по ссылке:\n{err}")

    def start_download(self):
        if self.is_downloading:
            return

        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Внимание", "Сначала вставьте и проанализируйте ссылку!")
            return

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⏳ СКАЧИВАНИЕ ФАЙЛА...", fg_color="#475569")
        self.finish_actions.pack_forget()

        # Parse Selection
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
            quality_sel = self.quality_var.get().lower()
            
            quality = "best"
            for res in ["4320p", "2160p", "1440p", "1080p", "720p", "480p", "360p", "240p", "144p"]:
                if res in quality_sel:
                    quality = res
                    break
            if "максимальн" in quality_sel or "best" in quality_sel:
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
        def progress_cb(progress_data):
            self.after(0, self._on_progress_update, progress_data)

        try:
            target_dir = self.dir_entry.get().strip() or self.download_dir
            import backend.downloader
            backend.downloader.DOWNLOADS_DIR = target_dir

            res = download_media_item(
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
        speed_text = f"⚡ {speed}   {('•  ⏱ ' + eta) if eta else ''}"
        self.speed_lbl.configure(text=speed_text)

        status = data.get("status", "")
        if status == "downloading":
            downloaded = format_bytes(data.get("downloaded_bytes"))
            total = data.get("total_bytes_formatted") or "--"
            self.status_lbl.configure(text=f"⬇️ Загружено: {int(pct*100)}% ({downloaded} / {total})")
        elif status == "finished":
            self.status_lbl.configure(text="🎬 Обработка и сшивание потоков через FFmpeg...")

    def _on_download_complete(self, res):
        self.is_downloading = False
        self.progress_bar.set(1.0)
        self.download_btn.configure(state="normal", text="⬇️ СКАЧАТЬ ЕЩЁ", fg_color=THEME["accent_green"])
        self.status_lbl.configure(text="✅ Файл успешно скачан и сохранён!")
        self.speed_lbl.configure(text="")

        if res and res.get("file_path"):
            self.last_downloaded_file = res.get("file_path")

        self.finish_actions.pack(fill="x", pady=(10, 0))

    def _on_download_error(self, err):
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⬇️ СКАЧАТЬ В МАКСИМАЛЬНОМ КАЧЕСТВЕ", fg_color=THEME["accent_green"])
        self.status_lbl.configure(text="❌ Произошла ошибка при скачивании")
        messagebox.showerror("Ошибка скачивания", f"Не удалось скачать медиафайл:\n{err}")

if __name__ == "__main__":
    app = UniDownloaderNativeApp()
    app.mainloop()
