"""
JARPISS - background download organizer

Install:   pip install customtkinter pywinstyles pystray pillow
Run:       pythonw jarpiss.py            (no console window)
Autostart: Settings -> "Start with Windows" (launches hidden in the tray)
Data:      %APPDATA%\\JARPISS\\config.json and error.log
"""
import copy
import ctypes
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    import pystray
    from PIL import Image, ImageDraw
except Exception:  # tray is optional; the app still works without it
    pystray = None

try:
    import pywinstyles
except Exception:
    pywinstyles = None

try:
    import winreg
except ImportError:  # not on Windows
    winreg = None

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

APP_NAME = "JARPISS"
USER_HOME = os.path.expanduser("~")
APPDATA = os.environ.get("APPDATA") or os.path.join(USER_HOME, ".config")
CONFIG_DIR = os.path.join(APPDATA, "JARPISS")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
LOG_PATH = os.path.join(CONFIG_DIR, "error.log")
IPC_PORT = 48653
HISTORY_LIMIT = 200
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

TEMP_EXTS = (".crdownload", ".part", ".partial", ".tmp", ".download", ".opdownload", ".!ut")
IGNORED_NAMES = ("desktop.ini", "thumbs.db")

ACCENT = "#1f6aa5"
GREEN = "#1d6b4a"
RED = "#a51f1f"
CARD = "#1b1b1b"
DEEP = "#121212"


def _p(folder, *parts):
    """Portable path: '{Pictures}' is resolved on each PC at runtime."""
    return os.path.join("{" + folder + "}", *parts)


DEFAULT_RULES = {
    # images
    ".png": _p("Pictures", "Images", "PNG"),
    ".jpg": _p("Pictures", "Images", "JPG"),
    ".jpeg": _p("Pictures", "Images", "JPG"),
    ".jfif": _p("Pictures", "Images", "JPG"),
    ".gif": _p("Pictures", "Images", "GIF"),
    ".webp": _p("Pictures", "Images", "WEBP"),
    ".svg": _p("Pictures", "Images", "SVG"),
    ".bmp": _p("Pictures", "Images", "BMP"),
    ".tiff": _p("Pictures", "Images", "TIFF"),
    ".tif": _p("Pictures", "Images", "TIFF"),
    ".ico": _p("Pictures", "Images", "ICO"),
    ".heic": _p("Pictures", "Images", "HEIC"),
    ".heif": _p("Pictures", "Images", "HEIC"),
    ".avif": _p("Pictures", "Images", "AVIF"),
    # camera raw
    ".cr2": _p("Pictures", "Raw Photos", "CR2"),
    ".nef": _p("Pictures", "Raw Photos", "NEF"),
    ".arw": _p("Pictures", "Raw Photos", "ARW"),
    ".dng": _p("Pictures", "Raw Photos", "DNG"),
    # design files
    ".psd": _p("Pictures", "Design", "PSD"),
    ".ai": _p("Pictures", "Design", "AI"),
    ".xcf": _p("Pictures", "Design", "XCF"),
    ".kra": _p("Pictures", "Design", "KRA"),
    # video
    ".mp4": _p("Videos", "Video Medias", "MP4"),
    ".mkv": _p("Videos", "Video Medias", "MKV"),
    ".avi": _p("Videos", "Video Medias", "AVI"),
    ".mov": _p("Videos", "Video Medias", "MOV"),
    ".webm": _p("Videos", "Video Medias", "WEBM"),
    ".wmv": _p("Videos", "Video Medias", "WMV"),
    ".flv": _p("Videos", "Video Medias", "FLV"),
    ".m4v": _p("Videos", "Video Medias", "M4V"),
    ".mpg": _p("Videos", "Video Medias", "MPEG"),
    ".mpeg": _p("Videos", "Video Medias", "MPEG"),
    ".3gp": _p("Videos", "Video Medias", "3GP"),
    # subtitles
    ".srt": _p("Videos", "Subtitles", "SRT"),
    ".ass": _p("Videos", "Subtitles", "ASS"),
    ".vtt": _p("Videos", "Subtitles", "VTT"),
    # audio
    ".mp3": _p("Music", "Audio", "MP3"),
    ".wav": _p("Music", "Audio", "WAV"),
    ".flac": _p("Music", "Audio", "FLAC"),
    ".m4a": _p("Music", "Audio", "M4A"),
    ".aac": _p("Music", "Audio", "AAC"),
    ".ogg": _p("Music", "Audio", "OGG"),
    ".opus": _p("Music", "Audio", "OPUS"),
    ".wma": _p("Music", "Audio", "WMA"),
    ".aiff": _p("Music", "Audio", "AIFF"),
    ".mid": _p("Music", "Audio", "MIDI"),
    ".midi": _p("Music", "Audio", "MIDI"),
    # documents
    ".pdf": _p("Documents", "Docs", "PDF"),
    ".docx": _p("Documents", "Docs", "DOCX"),
    ".doc": _p("Documents", "Docs", "DOC"),
    ".xlsx": _p("Documents", "Docs", "XLSX"),
    ".xls": _p("Documents", "Docs", "XLS"),
    ".pptx": _p("Documents", "Docs", "PPTX"),
    ".ppt": _p("Documents", "Docs", "PPT"),
    ".txt": _p("Documents", "Docs", "TXT"),
    ".csv": _p("Documents", "Docs", "CSV"),
    ".rtf": _p("Documents", "Docs", "RTF"),
    ".odt": _p("Documents", "Docs", "ODT"),
    ".ods": _p("Documents", "Docs", "ODS"),
    ".odp": _p("Documents", "Docs", "ODP"),
    ".md": _p("Documents", "Docs", "MD"),
    # ebooks
    ".epub": _p("Documents", "Ebooks", "EPUB"),
    ".mobi": _p("Documents", "Ebooks", "MOBI"),
    # fonts
    ".ttf": _p("Documents", "Fonts", "TTF"),
    ".otf": _p("Documents", "Fonts", "OTF"),
    # 3D models
    ".stl": _p("Documents", "3D Models", "STL"),
    ".obj": _p("Documents", "3D Models", "OBJ"),
    ".fbx": _p("Documents", "3D Models", "FBX"),
    ".blend": _p("Documents", "3D Models", "BLEND"),
    # archives
    ".zip": _p("Documents", "Compression", "ZIP"),
    ".rar": _p("Documents", "Compression", "RAR"),
    ".7z": _p("Documents", "Compression", "7Z"),
    ".tar": _p("Documents", "Compression", "TAR"),
    ".gz": _p("Documents", "Compression", "GZ"),
    ".bz2": _p("Documents", "Compression", "BZ2"),
    ".xz": _p("Documents", "Compression", "XZ"),
    ".tgz": _p("Documents", "Compression", "TGZ"),
    # code
    ".py": _p("Documents", "Code", "Python"),
    ".js": _p("Documents", "Code", "JavaScript"),
    ".ts": _p("Documents", "Code", "TypeScript"),
    ".html": _p("Documents", "Code", "HTML"),
    ".css": _p("Documents", "Code", "CSS"),
    ".json": _p("Documents", "Code", "JSON"),
    ".xml": _p("Documents", "Code", "XML"),
    ".java": _p("Documents", "Code", "Java"),
    ".cpp": _p("Documents", "Code", "C++"),
    ".c": _p("Documents", "Code", "C"),
    ".cs": _p("Documents", "Code", "CSharp"),
    ".lua": _p("Documents", "Code", "Lua"),
    ".luau": _p("Documents", "Code", "Lua"),
    ".go": _p("Documents", "Code", "Go"),
    ".rs": _p("Documents", "Code", "Rust"),
    ".php": _p("Documents", "Code", "PHP"),
    ".sql": _p("Documents", "Code", "SQL"),
    ".yaml": _p("Documents", "Code", "YAML"),
    ".yml": _p("Documents", "Code", "YAML"),
    ".sh": _p("Documents", "Code", "Scripts"),
    ".bat": _p("Documents", "Code", "Scripts"),
    ".ps1": _p("Documents", "Code", "Scripts"),
    # installers and apps
    ".exe": _p("Downloads", "Installers", "EXE"),
    ".msi": _p("Downloads", "Installers", "MSI"),
    ".iso": _p("Downloads", "Installers", "ISO"),
    ".apk": _p("Downloads", "Installers", "APK"),
    ".jar": _p("Downloads", "Installers", "JAR"),
    ".dmg": _p("Downloads", "Installers", "DMG"),
    ".deb": _p("Downloads", "Installers", "DEB"),
    # torrents
    ".torrent": _p("Downloads", "Torrents"),
}

DEFAULTS = {
    "watch_dir": _p("Downloads"),
    "interval": 3,
    "rules": DEFAULT_RULES,
    "auto_engine": True,
    "close_to_tray": True,
    "notifications": True,
    "date_subfolders": False,
    "total_moved": 0,
    "total_bytes": 0,
    "history": [],
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
_KNOWN_GUIDS = {
    "Documents": "FDD39AD0-238F-46AF-ADB4-6C85480369C7",
    "Downloads": "374DE290-123F-4565-9164-394A9C3A1A5A",
    "Music": "4BD8D571-6D19-48D3-BE97-422220080E43",
    "Pictures": "33E28130-4E1E-4676-835A-98395C3BC3BB",
    "Videos": "18989B1D-99B5-455B-841C-AB7C74E4DDFC",
}
_known_cache = {}


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]


def known_folder(name):
    """Real location of Downloads/Pictures/etc. (handles OneDrive redirects and renamed folders)."""
    if name in _known_cache:
        return _known_cache[name]
    path = os.path.join(USER_HOME, name)
    if sys.platform == "win32" and name in _KNOWN_GUIDS:
        try:
            u = uuid.UUID(_KNOWN_GUIDS[name])
            g = _GUID(u.time_low, u.time_mid, u.time_hi_version, (ctypes.c_ubyte * 8)(*u.bytes[8:]))
            buf = ctypes.c_wchar_p()
            fn = ctypes.windll.shell32.SHGetKnownFolderPath
            fn.argtypes = [ctypes.POINTER(_GUID), ctypes.c_ulong, ctypes.c_void_p,
                           ctypes.POINTER(ctypes.c_wchar_p)]
            fn.restype = ctypes.HRESULT
            fn(ctypes.byref(g), 0, None, ctypes.byref(buf))
            if buf.value:
                path = buf.value
            free = ctypes.windll.ole32.CoTaskMemFree
            free.argtypes = [ctypes.c_void_p]
            free(ctypes.cast(buf, ctypes.c_void_p))
        except Exception as e:
            log_error(f"known_folder({name}) failed: {e}")
    _known_cache[name] = path
    return path


def expand_path(p):
    """Turn '{Pictures}\\Images' into this PC's real path. Plain paths pass through unchanged."""
    if not isinstance(p, str) or "{" not in p:
        return p
    for name in _KNOWN_GUIDS:
        token = "{" + name + "}"
        if token in p:
            p = p.replace(token, known_folder(name))
    return p


def log_error(msg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    except Exception:
        pass


def fmt_size(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024


def pretty_path(p, limit=58):
    if p.startswith(USER_HOME):
        p = "~" + p[len(USER_HOME):]
    if len(p) > limit:
        p = p[:20] + "..." + p[-(limit - 23):]
    return p


def normalize_ext(text):
    t = text.strip().lower()
    if not t:
        return ""
    if not t.startswith("."):
        t = "." + t
    if len(t) < 2 or any(c in t for c in '\\/:*?"<>| '):
        return ""
    return t


def unique_path(folder, filename):
    dest = os.path.join(folder, filename)
    if not os.path.exists(dest):
        return dest
    stem, ext = os.path.splitext(filename)
    n = 1
    while True:
        cand = os.path.join(folder, f"{stem} ({n}){ext}")
        if not os.path.exists(cand):
            return cand
        n += 1


def open_path(path):
    try:
        os.makedirs(path, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        log_error(f"open_path failed: {e}")


def autostart_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --background'
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    return f'"{exe}" "{os.path.abspath(__file__)}" --background'


def autostart_enabled():
    if not winreg:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled):
    if not winreg:
        raise RuntimeError("Start with Windows only works on Windows.")
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if enabled:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except FileNotFoundError:
                pass


def sync_autostart():
    """If autostart is on but the stored command is stale (script moved), refresh it."""
    if not winreg or not autostart_enabled():
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            current, _ = winreg.QueryValueEx(k, APP_NAME)
        if current != autostart_command():
            set_autostart(True)
    except Exception as e:
        log_error(f"sync_autostart failed: {e}")


def make_tray_image(active):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = (31, 106, 165, 255) if active else (95, 95, 95, 255)
    d.rounded_rectangle((4, 4, 60, 60), radius=14, fill=base)
    d.polygon([(36, 10), (18, 36), (30, 36), (26, 54), (46, 26), (33, 26)], fill=(255, 255, 255, 255))
    return img


# --------------------------------------------------------------------------
# config (persisted in %APPDATA%)
# --------------------------------------------------------------------------
class Config:
    def __init__(self):
        self.lock = threading.RLock()
        self.data = copy.deepcopy(DEFAULTS)
        self.first_run = False
        self.load()

    def load(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except FileNotFoundError:
            self.first_run = True
            return
        except Exception as e:
            log_error(f"config load failed: {e}")
            return
        if not isinstance(loaded, dict):
            return
        for k, v in loaded.items():
            if k in DEFAULTS:
                self.data[k] = v
        # sanitise
        try:
            self.data["interval"] = max(1, min(30, int(self.data["interval"])))
        except (TypeError, ValueError):
            self.data["interval"] = 3
        if not isinstance(self.data["rules"], dict):
            self.data["rules"] = copy.deepcopy(DEFAULT_RULES)
        if not isinstance(self.data["history"], list):
            self.data["history"] = []

    def save(self):
        with self.lock:
            try:
                os.makedirs(CONFIG_DIR, exist_ok=True)
                tmp = CONFIG_PATH + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=2)
                os.replace(tmp, CONFIG_PATH)
            except Exception as e:
                log_error(f"config save failed: {e}")

    def __getitem__(self, key):
        value = self.data[key]
        return expand_path(value) if key == "watch_dir" else value

    def __setitem__(self, key, value):
        self.data[key] = value


# --------------------------------------------------------------------------
# engine (no UI code in here; talks to the UI through a queue)
# --------------------------------------------------------------------------
class Organizer:
    def __init__(self, cfg, events):
        self.cfg = cfg
        self.events = events
        self.running = False
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._scan_lock = threading.Lock()
        self._seen = {}
        self._errors = {}
        self._ignore = set()
        self._warned_missing = False

    def emit(self, *event):
        self.events.put(event)

    # control -------------------------------------------------------------
    def start(self):
        if self.running:
            return
        self._stop = threading.Event()
        self.running = True
        threading.Thread(target=self._loop, args=(self._stop,), daemon=True).start()

    def stop(self):
        self.running = False
        self._stop.set()
        self._wake.set()

    def scan_once_async(self):
        def work():
            try:
                self.organize_once()
                time.sleep(2.5)  # second pass confirms files are stable
                self.organize_once()
            except Exception as e:
                log_error(f"manual scan failed: {traceback.format_exc()}")
                self.emit("log", f"[ERROR] Scan failed: {e}")
        threading.Thread(target=work, daemon=True).start()

    def _loop(self, stop):
        while not stop.is_set():
            try:
                self.organize_once()
            except Exception as e:
                log_error(f"scan failed: {traceback.format_exc()}")
                self.emit("log", f"[ERROR] Scan failed: {e}")
            self._wake.wait(max(1, int(self.cfg["interval"])))
            self._wake.clear()

    # scanning ------------------------------------------------------------
    def _is_ready(self, path):
        try:
            st = os.stat(path)
        except OSError:
            return False
        sig = (st.st_size, st.st_mtime)
        if time.time() - st.st_mtime < 2 or self._seen.get(path) != sig:
            self._seen[path] = sig
            return False
        try:
            with open(path, "rb"):  # read-only probe: works on read-only files too
                pass
        except OSError:
            return False
        self._seen.pop(path, None)
        return True

    def organize_once(self):
        with self._scan_lock:
            watch = self.cfg["watch_dir"]
            if not os.path.isdir(watch):
                if not self._warned_missing:
                    self.emit("log", f"[WARN] Watch folder not found: {watch}")
                    self._warned_missing = True
                return 0
            self._warned_missing = False

            try:
                names = os.listdir(watch)
            except OSError as e:
                self.emit("log", f"[ERROR] Cannot read watch folder: {e}")
                return 0

            present = {os.path.join(watch, n) for n in names}
            for path in list(self._seen):
                if path not in present:
                    del self._seen[path]
            for path in list(self._errors):
                if path not in present:
                    del self._errors[path]
            present_norm = {os.path.normcase(p) for p in present}
            self._ignore &= present_norm

            with self.cfg.lock:
                rules = {k: expand_path(v) for k, v in self.cfg["rules"].items()}

            moved, last = 0, ""
            for name in names:
                src = os.path.join(watch, name)
                low = name.lower()
                if low.endswith(TEMP_EXTS) or low in IGNORED_NAMES or name.startswith(("~$", ".")):
                    continue
                if os.path.normcase(src) in self._ignore or self._errors.get(src, 0) >= 3:
                    continue
                if not os.path.isfile(src):
                    continue
                ext = os.path.splitext(low)[1]
                base_dir = rules.get(ext)
                if not base_dir:
                    continue
                if os.path.normcase(os.path.normpath(base_dir)) == os.path.normcase(os.path.normpath(watch)):
                    continue  # rule points at the watch folder itself
                if not self._is_ready(src):
                    continue
                if self._move(src, name, base_dir):
                    moved += 1
                    last = name

            if moved:
                self.cfg.save()
                self.emit("batch", moved, last)
            return moved

    def _move(self, src, name, base_dir):
        dest_dir = base_dir
        if self.cfg["date_subfolders"]:
            dest_dir = os.path.join(base_dir, datetime.now().strftime("%Y-%m"))
        try:
            os.makedirs(dest_dir, exist_ok=True)
            size = os.path.getsize(src)
            dest = unique_path(dest_dir, name)
            shutil.move(src, dest)
        except Exception as e:
            self._errors[src] = self._errors.get(src, 0) + 1
            tail = " (giving up on this file)" if self._errors[src] >= 3 else ""
            self.emit("log", f"[ERROR] {name}: {e}{tail}")
            return False

        with self.cfg.lock:
            self.cfg["total_moved"] += 1
            self.cfg["total_bytes"] += size
            hist = self.cfg["history"]
            hist.append({"t": time.time(), "name": os.path.basename(dest),
                         "src": src, "dest": dest, "size": size})
            del hist[:-HISTORY_LIMIT]
        self.emit("moved", os.path.basename(dest), os.path.basename(dest_dir), size)
        return True

    # undo ----------------------------------------------------------------
    def undo_async(self, entry):
        threading.Thread(target=self._undo, args=(entry,), daemon=True).start()

    def _undo(self, entry):
        with self._scan_lock:
            dest, src = entry["dest"], entry["src"]
            if not os.path.exists(dest):
                self.emit("log", f"[UNDO] {entry['name']} is no longer at its destination")
                return
            try:
                folder = os.path.dirname(src)
                os.makedirs(folder, exist_ok=True)
                target = unique_path(folder, os.path.basename(src))
                shutil.move(dest, target)
                self._ignore.add(os.path.normcase(target))  # don't re-sort it immediately
            except Exception as e:
                self.emit("log", f"[ERROR] Undo failed: {e}")
                return
            with self.cfg.lock:
                if entry in self.cfg["history"]:
                    self.cfg["history"].remove(entry)
                self.cfg["total_moved"] = max(0, self.cfg["total_moved"] - 1)
                self.cfg["total_bytes"] = max(0, self.cfg["total_bytes"] - entry.get("size", 0))
            self.cfg.save()
        self.emit("log", f"[UNDO] {entry['name']} restored to {pretty_path(os.path.dirname(src))}")
        self.emit("history")
        self.emit("stats")


# --------------------------------------------------------------------------
# single instance (second launch just asks the first one to show itself)
# --------------------------------------------------------------------------
def try_become_primary():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", IPC_PORT))
        s.listen(5)
        return s
    except OSError:
        s.close()
        return None


def signal_existing(msg):
    try:
        with socket.create_connection(("127.0.0.1", IPC_PORT), timeout=2) as c:
            c.sendall(msg)
            return c.recv(16).startswith(b"JARPISS-OK")  # make sure it's really us
    except OSError:
        return False


def start_ipc_listener(server, events):
    def run():
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                return
            try:
                conn.settimeout(1)
                if conn.recv(16).startswith(b"show"):
                    events.put(("show",))
                conn.sendall(b"JARPISS-OK")
            except Exception:
                pass
            finally:
                conn.close()
    threading.Thread(target=run, daemon=True).start()


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
class JarpissApp(ctk.CTk):
    def __init__(self, background=False):
        super().__init__()
        self.cfg = Config()
        self.events = queue.Queue()
        self.engine = Organizer(self.cfg, self.events)
        self.visible = not background
        self.session_moved = 0
        self.session_bytes = 0
        self.tray = None
        self.current_page = "dashboard"
        self._slider_job = None

        self.title("JARPISS")
        self.geometry("920x640")
        self.minsize(840, 580)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.f_title = ctk.CTkFont(family="Segoe UI", size=24, weight="bold")
        self.f_big = ctk.CTkFont(family="Segoe UI", size=26, weight="bold")
        self.f_ui = ctk.CTkFont(family="Segoe UI", size=13)
        self.f_bold = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        self.f_small = ctk.CTkFont(family="Segoe UI", size=11)
        self.f_mono = ctk.CTkFont(family="Consolas", size=11)

        first_run = self.cfg.first_run and not background
        if first_run:
            self.cfg["auto_engine"] = False  # don't touch a stranger's files before they say so

        self.build_ui()
        if pywinstyles:
            try:
                pywinstyles.apply_style(self, "mica")
            except Exception:
                pass

        self.build_tray()
        sync_autostart()
        self.show_page("dashboard")
        self.refresh_stats()
        self.after(150, self._pump)

        if background:
            self.withdraw()
            self.after(400, self._enforce_hidden)
        if first_run:
            self.refresh_state()
            self.after(700, self.first_run_prompt)
        elif self.cfg["auto_engine"]:
            self.start_engine()
        else:
            self.refresh_state()

    def first_run_prompt(self):
        start = messagebox.askyesno(
            "Welcome to JARPISS",
            f"JARPISS sorts the files in:\n{self.cfg['watch_dir']}\n\n"
            "into folders by type. Every move can be undone from the History tab, "
            "and you can change where things go in the Rules tab.\n\n"
            "Start organizing now?")
        self.cfg["auto_engine"] = bool(start)
        self.cfg.save()
        if start:
            self.start_engine()

    def report_callback_exception(self, exc, val, tb):
        log_error("".join(traceback.format_exception(exc, val, tb)))

    # layout ---------------------------------------------------------------
    def build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=190, corner_radius=0, fg_color="#141414")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="JARPISS", font=self.f_title).pack(anchor="w", padx=20, pady=(26, 0))
        ctk.CTkLabel(self.sidebar, text="download organizer", font=self.f_small,
                     text_color="#777777").pack(anchor="w", padx=21, pady=(0, 22))

        self.nav_buttons = {}
        for key, label in (("dashboard", "Dashboard"), ("rules", "Rules"),
                           ("history", "History"), ("settings", "Settings")):
            b = ctk.CTkButton(self.sidebar, text=label, anchor="w", height=38, corner_radius=8,
                              fg_color="transparent", hover_color="#262626", text_color="#cfcfcf",
                              font=self.f_ui, command=lambda k=key: self.show_page(k))
            b.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = b

        self.side_status = ctk.CTkLabel(self.sidebar, text="Engine idle", font=self.f_small,
                                        text_color="#888888")
        self.side_status.pack(side="bottom", anchor="w", padx=20, pady=18)

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.pages = {}
        for key, builder in (("dashboard", self.build_dashboard), ("rules", self.build_rules),
                             ("history", self.build_history), ("settings", self.build_settings)):
            page = ctk.CTkFrame(self.content, fg_color="transparent")
            page.grid(row=0, column=0, sticky="nsew")
            builder(page)
            self.pages[key] = page

    def show_page(self, key):
        self.current_page = key
        self.pages[key].tkraise()
        for k, b in self.nav_buttons.items():
            b.configure(fg_color="#232a33" if k == key else "transparent")
        if key == "history":
            self.refresh_history()

    def page_header(self, page, title, right_widget_factory=None):
        head = ctk.CTkFrame(page, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 10))
        ctk.CTkLabel(head, text=title, font=self.f_title).pack(side="left")
        if right_widget_factory:
            right_widget_factory(head).pack(side="right")
        return head

    # dashboard ------------------------------------------------------------
    def build_dashboard(self, page):
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(3, weight=1)

        def pill(parent):
            self.pill = ctk.CTkLabel(parent, text="IDLE", font=self.f_bold, fg_color="#333333",
                                     corner_radius=12, width=90, height=26)
            return self.pill
        self.page_header(page, "Dashboard", pill)

        cards = ctk.CTkFrame(page, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=22, pady=4)
        for i in range(3):
            cards.grid_columnconfigure(i, weight=1, uniform="cards")
        self.card_total = self.make_card(cards, 0, "Total files moved")
        self.card_size = self.make_card(cards, 1, "Total data moved")
        self.card_session = self.make_card(cards, 2, "This session")

        ctrl = ctk.CTkFrame(page, fg_color="transparent")
        ctrl.grid(row=2, column=0, sticky="ew", padx=28, pady=(14, 8))
        self.btn_toggle = ctk.CTkButton(ctrl, text="Start Engine", font=self.f_ui, width=130,
                                        fg_color=ACCENT, hover_color="#144870", command=self.toggle_engine)
        self.btn_toggle.pack(side="left", padx=(0, 8))
        for text, cmd in (("Scan Now", self.scan_now), ("Gen Test Files", self.generate_test_files),
                          ("Open Folder", self.open_watch)):
            ctk.CTkButton(ctrl, text=text, font=self.f_ui, width=110, fg_color="#2b2b2b",
                          hover_color="#3a3a3a", command=cmd).pack(side="left", padx=4)

        self.log_area = ctk.CTkTextbox(page, font=self.f_mono, state="disabled", fg_color=DEEP,
                                       border_width=1, border_color="#2a2a2a")
        self.log_area.grid(row=3, column=0, sticky="nsew", padx=28, pady=(6, 24))

    def make_card(self, parent, col, caption):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12)
        card.grid(row=0, column=col, sticky="ew", padx=6)
        value = ctk.CTkLabel(card, text="0", font=self.f_big)
        value.pack(anchor="w", padx=18, pady=(16, 0))
        ctk.CTkLabel(card, text=caption, font=self.f_small, text_color="#888888").pack(
            anchor="w", padx=19, pady=(0, 14))
        return value

    # rules ----------------------------------------------------------------
    def build_rules(self, page):
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)

        def reset_btn(parent):
            return ctk.CTkButton(parent, text="Defaults...", width=110, font=self.f_ui,
                                 fg_color="#2b2b2b", hover_color="#3a3a3a", command=self.reset_rules)
        self.page_header(page, "Rules", reset_btn)

        add = ctk.CTkFrame(page, fg_color=CARD, corner_radius=10)
        add.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 10))
        add.grid_columnconfigure(1, weight=1)
        self.new_ext = ctk.CTkEntry(add, width=90, placeholder_text=".ext", font=self.f_ui)
        self.new_ext.grid(row=0, column=0, padx=(12, 6), pady=12)
        self.new_dir = ctk.CTkEntry(add, placeholder_text="Destination folder", font=self.f_ui)
        self.new_dir.grid(row=0, column=1, sticky="ew", padx=6)
        ctk.CTkButton(add, text="Browse", width=70, fg_color="#2b2b2b", hover_color="#3a3a3a",
                      font=self.f_ui, command=lambda: self.browse_into(self.new_dir)).grid(row=0, column=2, padx=4)
        ctk.CTkButton(add, text="Add rule", width=80, fg_color=ACCENT, hover_color="#144870",
                      font=self.f_ui, command=self.add_rule).grid(row=0, column=3, padx=(4, 12))

        self.rules_list = ctk.CTkScrollableFrame(page, fg_color=DEEP, corner_radius=10)
        self.rules_list.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 24))
        self.refresh_rules()

    def refresh_rules(self):
        for w in self.rules_list.winfo_children():
            w.destroy()
        with self.cfg.lock:
            items = sorted(self.cfg["rules"].items())
        for ext, folder in items:
            row = ctk.CTkFrame(self.rules_list, fg_color=CARD, corner_radius=8)
            row.pack(fill="x", pady=3, padx=2)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=ext, width=70, anchor="w", font=self.f_bold).grid(
                row=0, column=0, padx=(12, 6), pady=8)
            ctk.CTkLabel(row, text=pretty_path(expand_path(folder)), anchor="w", font=self.f_ui,
                         text_color="#aaaaaa").grid(row=0, column=1, sticky="ew")
            ctk.CTkButton(row, text="Change", width=70, height=26, font=self.f_small, fg_color="#2b2b2b",
                          hover_color="#3a3a3a", command=lambda e=ext: self.change_rule(e)).grid(row=0, column=2)
            ctk.CTkButton(row, text="Remove", width=70, height=26, font=self.f_small, fg_color="#4a2222",
                          hover_color="#6a2c2c", command=lambda e=ext: self.remove_rule(e)).grid(
                row=0, column=3, padx=(4, 10))

    def browse_into(self, entry):
        d = filedialog.askdirectory()
        if d:
            entry.delete(0, "end")
            entry.insert(0, os.path.normpath(d))

    def add_rule(self):
        ext = normalize_ext(self.new_ext.get())
        folder = self.new_dir.get().strip()
        if not ext:
            messagebox.showerror("JARPISS", "Enter a valid extension, like .png")
            return
        folder = expand_path(folder)
        if not folder or not os.path.isabs(folder):
            messagebox.showerror("JARPISS", "Pick a full destination folder path.")
            return
        with self.cfg.lock:
            self.cfg["rules"][ext] = os.path.normpath(folder)
        self.cfg.save()
        self.new_ext.delete(0, "end")
        self.new_dir.delete(0, "end")
        self.refresh_rules()

    def change_rule(self, ext):
        d = filedialog.askdirectory(initialdir=expand_path(self.cfg["rules"].get(ext, USER_HOME)))
        if d:
            with self.cfg.lock:
                self.cfg["rules"][ext] = os.path.normpath(d)
            self.cfg.save()
            self.refresh_rules()

    def remove_rule(self, ext):
        with self.cfg.lock:
            self.cfg["rules"].pop(ext, None)
        self.cfg.save()
        self.refresh_rules()

    def reset_rules(self):
        ans = messagebox.askyesnocancel(
            "JARPISS",
            "Add any missing default rules and keep your own?\n\n"
            "Yes = add the missing defaults (your changes stay)\n"
            "No = replace everything with the defaults\n"
            "Cancel = do nothing")
        if ans is None:
            return
        with self.cfg.lock:
            if ans:
                for ext, folder in DEFAULT_RULES.items():
                    self.cfg["rules"].setdefault(ext, folder)
            else:
                self.cfg["rules"] = copy.deepcopy(DEFAULT_RULES)
        self.cfg.save()
        self.refresh_rules()

    # history --------------------------------------------------------------
    def build_history(self, page):
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        def clear_btn(parent):
            return ctk.CTkButton(parent, text="Clear history", width=120, font=self.f_ui,
                                 fg_color="#2b2b2b", hover_color="#3a3a3a", command=self.clear_history)
        self.page_header(page, "History", clear_btn)
        self.history_list = ctk.CTkScrollableFrame(page, fg_color=DEEP, corner_radius=10)
        self.history_list.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 24))

    def refresh_history(self):
        for w in self.history_list.winfo_children():
            w.destroy()
        with self.cfg.lock:
            entries = list(self.cfg["history"])[-60:][::-1]
        if not entries:
            ctk.CTkLabel(self.history_list, text="Nothing moved yet.", font=self.f_ui,
                         text_color="#777777").pack(pady=30)
            return
        for entry in entries:
            row = ctk.CTkFrame(self.history_list, fg_color=CARD, corner_radius=8)
            row.pack(fill="x", pady=3, padx=2)
            row.grid_columnconfigure(1, weight=1)
            when = datetime.fromtimestamp(entry["t"]).strftime("%b %d  %H:%M")
            ctk.CTkLabel(row, text=when, width=96, anchor="w", font=self.f_small,
                         text_color="#888888").grid(row=0, column=0, padx=(12, 4), pady=8)
            info = f"{entry['name']}   ->   {pretty_path(os.path.dirname(entry['dest']), 40)}"
            ctk.CTkLabel(row, text=info, anchor="w", font=self.f_ui).grid(row=0, column=1, sticky="ew")
            ctk.CTkButton(row, text="Undo", width=60, height=26, font=self.f_small, fg_color="#2b2b2b",
                          hover_color="#3a3a3a", command=lambda e=entry: self.engine.undo_async(e)).grid(
                row=0, column=2, padx=(4, 10))

    def clear_history(self):
        with self.cfg.lock:
            self.cfg["history"] = []
        self.cfg.save()
        self.refresh_history()

    # settings -------------------------------------------------------------
    def build_settings(self, page):
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        self.page_header(page, "Settings")
        body = ctk.CTkScrollableFrame(page, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 18))

        # watch folder
        row = self.setting_row(body, "Watch folder", "The folder JARPISS keeps tidy")
        self.watch_lbl = ctk.CTkLabel(row, text=pretty_path(self.cfg["watch_dir"], 34), font=self.f_small,
                                      text_color="#aaaaaa")
        self.watch_lbl.pack(side="right", padx=(0, 6))
        ctk.CTkButton(row, text="Browse", width=70, font=self.f_ui, fg_color="#2b2b2b",
                      hover_color="#3a3a3a", command=self.change_watch).pack(side="right", padx=8)

        # interval
        row = self.setting_row(body, "Scan interval", "Seconds between checks")
        self.interval_lbl = ctk.CTkLabel(row, text=f"{self.cfg['interval']} s", width=40, font=self.f_ui)
        self.interval_lbl.pack(side="right", padx=(4, 12))
        slider = ctk.CTkSlider(row, from_=1, to=30, number_of_steps=29, width=170, command=self.on_interval)
        slider.set(self.cfg["interval"])
        slider.pack(side="right")

        # switches
        self.var_autostart = ctk.BooleanVar(value=autostart_enabled())
        sw = self.switch_row(body, "Start with Windows",
                             "Launches hidden in the tray at login" if winreg else "Only available on Windows",
                             self.var_autostart, self.on_autostart)
        if not winreg:
            sw.configure(state="disabled")
        self.flag_row(body, "Start engine automatically", "Begin organizing as soon as JARPISS opens", "auto_engine")
        self.flag_row(body, "Close button hides to tray", "Off = the X button quits the app", "close_to_tray")
        self.flag_row(body, "Tray notifications", "Pop a notice when files are moved while hidden", "notifications")
        self.flag_row(body, "Group by month", "Put files in YYYY-MM subfolders inside each destination",
                      "date_subfolders")

        row = self.setting_row(body, "App data", f"Config and error log: {pretty_path(CONFIG_DIR, 46)}")
        ctk.CTkButton(row, text="Open", width=70, font=self.f_ui, fg_color="#2b2b2b", hover_color="#3a3a3a",
                      command=lambda: open_path(CONFIG_DIR)).pack(side="right", padx=12)

    def setting_row(self, parent, title, desc):
        row = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=10, height=62)
        row.pack(fill="x", pady=4, padx=6)
        row.pack_propagate(False)
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.pack(side="left", padx=16)
        ctk.CTkLabel(text, text=title, font=self.f_bold, anchor="w").pack(anchor="w")
        ctk.CTkLabel(text, text=desc, font=self.f_small, text_color="#888888", anchor="w").pack(anchor="w")
        return row

    def switch_row(self, parent, title, desc, var, command):
        row = self.setting_row(parent, title, desc)
        sw = ctk.CTkSwitch(row, text="", variable=var, command=command, width=44)
        sw.pack(side="right", padx=14)
        return sw

    def flag_row(self, parent, title, desc, key):
        var = ctk.BooleanVar(value=bool(self.cfg[key]))

        def on_toggle():
            self.cfg[key] = bool(var.get())
            self.cfg.save()
        self.switch_row(parent, title, desc, var, on_toggle)

    def change_watch(self):
        d = filedialog.askdirectory(initialdir=self.cfg["watch_dir"])
        if d:
            self.cfg["watch_dir"] = os.path.normpath(d)
            self.cfg.save()
            self.watch_lbl.configure(text=pretty_path(self.cfg["watch_dir"], 34))
            self.log(f"Now watching {self.cfg['watch_dir']}")

    def on_interval(self, value):
        self.cfg["interval"] = int(round(value))
        self.interval_lbl.configure(text=f"{self.cfg['interval']} s")
        if self._slider_job:
            self.after_cancel(self._slider_job)
        self._slider_job = self.after(500, self.cfg.save)

    def on_autostart(self):
        want = self.var_autostart.get()
        try:
            set_autostart(want)
        except Exception as e:
            self.var_autostart.set(not want)
            messagebox.showerror("JARPISS", str(e))

    # engine control ---------------------------------------------------------
    def start_engine(self):
        self.engine.start()
        self.refresh_state()
        self.log(f"Engine started, watching {self.cfg['watch_dir']}")

    def stop_engine(self):
        self.engine.stop()
        self.refresh_state()
        self.log("Engine stopped.")

    def toggle_engine(self):
        if self.engine.running:
            self.stop_engine()
        else:
            self.start_engine()

    def scan_now(self):
        self.log("Manual scan...")
        self.engine.scan_once_async()

    def open_watch(self):
        open_path(self.cfg["watch_dir"])

    def generate_test_files(self):
        watch = self.cfg["watch_dir"]
        tests = [("dummy_doc.docx", "test doc content"),
                 ("script_test.py", "print('hello from jarpiss')"),
                 ("pic_test.jpg", "fake image byte stream")]
        try:
            os.makedirs(watch, exist_ok=True)
            for fname, content in tests:
                with open(unique_path(watch, fname), "w", encoding="utf-8") as f:
                    f.write(content)
            self.log("Generated test files in the watch folder.")
        except OSError as e:
            self.log(f"[ERROR] Could not create test files: {e}")

    def refresh_state(self):
        running = self.engine.running
        self.btn_toggle.configure(text="Stop Engine" if running else "Start Engine",
                                  fg_color=RED if running else ACCENT,
                                  hover_color="#701414" if running else "#144870")
        self.pill.configure(text="RUNNING" if running else "IDLE", fg_color=GREEN if running else "#333333")
        self.side_status.configure(text="Engine running" if running else "Engine idle",
                                   text_color="#4cc38a" if running else "#888888")
        self.update_tray()

    def refresh_stats(self):
        self.card_total.configure(text=f"{self.cfg['total_moved']:,}")
        self.card_size.configure(text=fmt_size(self.cfg["total_bytes"]))
        self.card_session.configure(text=f"{self.session_moved}  ({fmt_size(self.session_bytes)})")

    def log(self, text):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", f"{datetime.now():%H:%M:%S}  {text}\n")
        lines = int(self.log_area.index("end-1c").split(".")[0])
        if lines > 600:
            self.log_area.delete("1.0", f"{lines - 500}.0")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    # tray -----------------------------------------------------------------
    def build_tray(self):
        if not pystray:
            log_error("pystray/Pillow not available; running without a tray icon")
            return
        menu = pystray.Menu(
            pystray.MenuItem("Open JARPISS", lambda i, it: self.cmd("show"), default=True),
            pystray.MenuItem(lambda it: "Stop Engine" if self.engine.running else "Start Engine",
                             lambda i, it: self.cmd("toggle")),
            pystray.MenuItem("Scan Now", lambda i, it: self.cmd("scan")),
            pystray.MenuItem("Open Watch Folder", lambda i, it: self.cmd("open_watch")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda i, it: self.cmd("quit")),
        )
        try:
            self.tray = pystray.Icon(APP_NAME, make_tray_image(False), "JARPISS", menu)
            threading.Thread(target=self.tray.run, daemon=True).start()
        except Exception as e:
            log_error(f"tray failed to start: {e}")
            self.tray = None

    def cmd(self, name):
        # called from the tray thread; the Tk thread picks it up in _pump
        self.events.put(("cmd", name))

    def update_tray(self):
        if not self.tray:
            return
        try:
            self.tray.icon = make_tray_image(self.engine.running)
            self.tray.title = "JARPISS - " + ("running" if self.engine.running else "idle")
            self.tray.update_menu()
        except Exception as e:
            log_error(f"update_tray failed: {e}")

    # window visibility ----------------------------------------------------
    def _enforce_hidden(self):
        if not self.visible:
            self.withdraw()

    def show_window(self):
        self.visible = True
        self.deiconify()
        self.state("normal")
        self.lift()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))
        self.focus_force()
        self.refresh_stats()
        if self.current_page == "history":
            self.refresh_history()

    def hide_window(self):
        self.visible = False
        self.withdraw()

    def on_close(self):
        if self.cfg["close_to_tray"] and self.tray:
            self.hide_window()
        else:
            self.quit_app()

    def quit_app(self):
        self.engine.stop()
        self.cfg.save()
        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass
        self.destroy()

    # event pump (all UI work happens on the Tk thread) ----------------------
    def _pump(self):
        try:
            while True:
                self._handle(self.events.get_nowait())
        except queue.Empty:
            pass
        except Exception:
            log_error(traceback.format_exc())
        self.after(150, self._pump)

    def _handle(self, ev):
        kind = ev[0]
        if kind == "log":
            self.log(ev[1])
        elif kind == "moved":
            _, name, folder, size = ev
            self.session_moved += 1
            self.session_bytes += size
            self.log(f"[MOVED] {name} -> {folder}")
            self.refresh_stats()
            if self.current_page == "history":
                self.refresh_history()
        elif kind == "batch":
            _, count, last = ev
            if self.cfg["notifications"] and not self.visible and self.tray:
                msg = f"Moved {last}" if count == 1 else f"Moved {count} files"
                try:
                    self.tray.notify(msg, "JARPISS")
                except Exception:
                    pass
        elif kind == "stats":
            self.refresh_stats()
        elif kind == "history":
            if self.current_page == "history":
                self.refresh_history()
        elif kind == "show":
            self.show_window()
        elif kind == "cmd":
            name = ev[1]
            if name == "show":
                self.show_window()
            elif name == "toggle":
                self.toggle_engine()
            elif name == "scan":
                self.scan_now()
            elif name == "open_watch":
                self.open_watch()
            elif name == "quit":
                self.quit_app()


def main():
    background = "--background" in sys.argv
    server = try_become_primary()
    if server is None and signal_existing(b"noop" if background else b"show"):
        return  # already running; the existing instance handles it
    app = JarpissApp(background=background)
    if server:
        start_ipc_listener(server, app.events)
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_error(traceback.format_exc())
        raise