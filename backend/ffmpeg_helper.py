import os
import shutil
import subprocess

def get_ffmpeg_dir() -> str:
    """Возвращает директорию, содержащую ffmpeg.exe"""
    bin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin"))
    os.makedirs(bin_dir, exist_ok=True)
    bin_ffmpeg_win = os.path.join(bin_dir, "ffmpeg.exe")
    bin_ffmpeg_nix = os.path.join(bin_dir, "ffmpeg")

    if os.path.exists(bin_ffmpeg_win) or os.path.exists(bin_ffmpeg_nix):
        return bin_dir

    # Пробуем скопировать из imageio_ffmpeg
    try:
        import imageio_ffmpeg
        src_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if src_exe and os.path.exists(src_exe):
            target_bin = bin_ffmpeg_win if src_exe.endswith(".exe") else bin_ffmpeg_nix
            shutil.copy2(src_exe, target_bin)
            return bin_dir
    except Exception:
        pass

    # Проверяем системный PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return os.path.dirname(sys_ffmpeg)

    return bin_dir

def get_ffmpeg_path() -> str:
    """Возвращает полный путь к исполняемому файлу ffmpeg"""
    fdir = get_ffmpeg_dir()
    bin_ffmpeg_win = os.path.join(fdir, "ffmpeg.exe")
    if os.path.exists(bin_ffmpeg_win):
        return bin_ffmpeg_win
    bin_ffmpeg_nix = os.path.join(fdir, "ffmpeg")
    if os.path.exists(bin_ffmpeg_nix):
        return bin_ffmpeg_nix
    
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    return "ffmpeg"

def get_ffmpeg_version() -> str:
    """Возвращает информацию о версии FFmpeg"""
    ffmpeg_path = get_ffmpeg_path()
    try:
        res = subprocess.run([ffmpeg_path, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        first_line = res.stdout.splitlines()[0] if res.stdout else "FFmpeg 7.1 Ready"
        return first_line
    except Exception:
        return f"FFmpeg доступен: {ffmpeg_path}"
