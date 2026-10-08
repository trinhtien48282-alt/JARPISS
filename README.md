# JARPISS

**JARPISS** is a Windows background download organizer that automatically sorts files into configurable folders based on their file extensions.

> **J**ust **A** **R**ather **P**ersistent **I**ntelligent **S**orting **S**ystem

JARPISS quietly watches a folder, waits for downloads to finish, and moves supported files into organized destinations.

Built originally in Python. Currently being migrated to a native C++ implementation.

---

## ✨ Features

* 📁 Automatic file organization
* ⚙️ Configurable extension → destination rules
* ⏳ Stable-file detection for files that are still downloading
* 🔢 Automatic duplicate filename handling
* ↩️ Move history and undo
* 📊 Total files and bytes moved
* 🔔 Optional tray notifications
* 🪟 Windows system tray
* 🚀 Start with Windows
* 👻 Background mode
* 🔒 Single-instance protection
* 📅 Optional monthly destination folders
* 🧪 Test-file generator
* 📝 Persistent configuration and error logging

---

## 🖥️ Example

A downloaded file such as:

```text
photo.png
```

can automatically become:

```text
Pictures/
└── Images/
    └── PNG/
        └── photo.png
```

A PDF can become:

```text
Documents/
└── Docs/
    └── PDF/
        └── document.pdf
```

Rules are configurable, so JARPISS does not force a fixed folder structure.

---

## 🧠 How It Works

JARPISS periodically scans the configured watch folder.

For each file, it:

1. Checks whether the file should be ignored.
2. Checks whether the file is still being written.
3. Determines its extension.
4. Looks up the configured destination.
5. Creates the destination directory if necessary.
6. Generates a unique filename if a conflict exists.
7. Moves the file.
8. Records the operation in history.
9. Updates statistics.
10. Reports the result to the application.

Temporary download files such as:

```text
.crdownload
.part
.partial
.tmp
.download
.opdownload
.!ut
```

are ignored until they become normal files.

---

## 📂 Data Location

JARPISS stores its application data in:

```text
%APPDATA%\JARPISS\
```

Files include:

```text
config.json
error.log
```

The configuration contains:

* Watch folder
* Scan interval
* Rules
* Engine settings
* Notification settings
* Statistics
* Move history

---

## ⚙️ Default Organization

The default rules cover common categories including:

### Images

```text
PNG
JPG
GIF
WEBP
SVG
BMP
TIFF
ICO
HEIC
AVIF
```

### Raw Photos

```text
CR2
NEF
ARW
DNG
```

### Video

```text
MP4
MKV
AVI
MOV
WEBM
WMV
FLV
M4V
MPEG
3GP
```

### Audio

```text
MP3
WAV
FLAC
M4A
AAC
OGG
OPUS
WMA
AIFF
MIDI
```

### Documents

```text
PDF
DOC
DOCX
XLS
XLSX
PPT
PPTX
TXT
CSV
RTF
ODT
ODS
ODP
MD
```

### Code

```text
PY
JS
TS
HTML
CSS
JSON
XML
JAVA
CPP
C
CS
LUA
LUAU
GO
RS
PHP
SQL
YAML
SH
BAT
PS1
```

### Archives

```text
ZIP
RAR
7Z
TAR
GZ
BZ2
XZ
TGZ
```

### Installers

```text
EXE
MSI
ISO
APK
JAR
DMG
DEB
```

### Torrents

```text
TORRENT
```

---

## 🔄 Undo

Every successful move is recorded in JARPISS history.

For example:

```text
Downloads\image.png
        ↓
Pictures\Images\PNG\image.png
```

The move can later be undone from the History page.

If the original location no longer exists, JARPISS recreates it when possible.

If a filename collision exists during undo, JARPISS generates a unique filename instead of overwriting an existing file.

---

## 🗓️ Monthly Folders

JARPISS can optionally group moved files by month.

For example:

```text
Pictures/
└── Images/
    └── PNG/
        └── 2026-10/
            └── image.png
```

This is controlled by the **Group by month** setting.

---

## 🪟 Windows Integration

JARPISS is designed primarily for Windows.

Windows-specific functionality includes:

* Known-folder resolution
* Registry-based startup
* System tray
* Background startup
* Single-instance communication
* Folder opening
* Native filesystem operations

The application does not assume that folders such as `Downloads` or `Pictures` necessarily exist directly under the user's home directory. Windows known-folder APIs are used by the native implementation.

---

## 🚧 C++ Migration

JARPISS is being migrated from Python to native C++.

The original Python implementation remains the behavioral reference during migration.

The migration is intentionally incremental:

```text
Python implementation
        │
        ▼
C++ project skeleton
        │
        ▼
Configuration
        │
        ▼
Windows path handling
        │
        ▼
Organizer engine
        │
        ▼
File movement + undo
        │
        ▼
Background workers
        │
        ▼
Single-instance IPC
        │
        ▼
Windows autostart
        │
        ▼
Native GUI
        │
        ▼
System tray
        │
        ▼
Background mode
        │
        ▼
Regression testing
        │
        ▼
Native C++ release
```

See [`ROADMAP.md`](ROADMAP.md) for the complete migration plan.

---

## 🏗️ Project Structure

The target architecture separates core behavior from Windows-specific functionality and UI:

```text
src/
├── core/
│   ├── organizer
│   ├── config
│   └── rules
│
├── platform/
│   ├── known folders
│   ├── autostart
│   ├── single instance
│   └── Windows utilities
│
├── ui/
│   ├── dashboard
│   ├── rules
│   ├── history
│   └── settings
│
└── util/
    ├── logging
    └── formatting
```

The exact implementation may evolve during the migration.

---

## 🧪 Development

The project is being developed incrementally.

The current migration policy is:

* Keep the Python implementation unchanged.
* Treat Python behavior as the reference.
* Implement one migration stage at a time.
* Build after each stage.
* Test behavior before advancing.
* Avoid unnecessary dependencies.
* Avoid silent behavioral changes.

---

## 🛡️ Safety

JARPISS is designed to avoid destructive file operations.

In particular:

* Files are not silently overwritten.
* Duplicate names receive unique filenames.
* Temporary download files are ignored.
* Files that are still changing are not immediately moved.
* Move history is retained for undo.
* Ordinary filesystem failures are logged rather than treated as successful moves.

Even so, users should keep backups of important data.

---

## 📜 Original Python Dependencies

The original Python implementation uses:

```text
customtkinter
pywinstyles
pystray
Pillow
```

The native C++ version is intended to eventually operate without requiring the Python runtime.

---

## 📄 License

License information will be added when the project license is finalized.

---

## 🚂 Project Status

**Migration in progress.**

The Python implementation is the current behavioral reference while the native C++ version is developed.

The destination is a lightweight, native Windows utility that can sit quietly in the system tray and keep the Downloads folder from turning into digital archaeological strata. 💀
