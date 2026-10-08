# JARPISS C++ Migration Roadmap

## Purpose

This document defines the controlled migration of JARPISS from its current Python implementation to a native C++ Windows application.

The existing Python implementation is the **behavioral reference**.

The C++ implementation must reproduce the existing behavior unless a specific stage explicitly authorizes a behavior change.

---

# Core Migration Rules

These rules apply to every stage.

1. **Python is the behavioral reference.**

   * Read the existing Python implementation before porting functionality.
   * Preserve its behavior unless explicitly instructed otherwise.

2. **Do not rewrite the Python implementation.**

   * The Python version remains available for behavioral comparison and regression testing.

3. **Do not "improve" behavior during migration.**

   * Do not silently change algorithms.
   * Do not replace timing behavior.
   * Do not alter defaults.
   * Do not redesign configuration formats.
   * Do not remove edge-case handling.
   * Do not optimize behavior unless explicitly requested.

4. **One stage at a time.**

   * Complete the requested stage.
   * Build and test it.
   * Report the result.
   * Stop.
   * Do not automatically continue into the next stage.

5. **Keep the project buildable.**

   * Every completed stage must leave the C++ project in a buildable state.

6. **Prefer small, understandable modules.**

   * Avoid a giant `main.cpp`.
   * Keep platform-specific Windows code separated from core organizer logic.
   * Keep UI code separated from the engine.

7. **Do not introduce unnecessary dependencies.**

   * Prefer the C++ standard library and Windows APIs where appropriate.
   * Third-party dependencies require a concrete reason.

8. **Preserve user data compatibility whenever possible.**

   * Existing JARPISS configuration and history should remain usable by the C++ version unless a stage explicitly defines a migration.

9. **Do not delete Python source code.**

10. **Never claim a stage is complete without building/testing it.**

---

# Behavioral Reference

The Python implementation currently provides:

* Background download organization
* Extension-based file rules
* Stable-file detection
* Duplicate filename handling
* Persistent JSON configuration
* Error logging
* File history
* Undo
* File/byte statistics
* Windows known-folder resolution
* Windows startup integration
* Single-instance protection
* Local IPC
* System tray
* Background startup
* Tray notifications
* GUI
* Settings
* Manual scanning
* Test-file generation
* Optional date-based destination folders

Important existing constants and defaults include:

* Application name: `JARPISS`
* IPC port: `48653`
* History limit: `200`
* Default scan interval: `3` seconds
* Allowed scan interval: `1` to `30` seconds
* Configuration directory: `%APPDATA%\JARPISS`
* Configuration file: `%APPDATA%\JARPISS\config.json`
* Error log: `%APPDATA%\JARPISS\error.log`

The complete Python source must be inspected before implementing corresponding C++ behavior.

---

# Target Architecture

The final C++ project should approximately follow this structure:

```text
JARPISS/
├── CMakeLists.txt
├── README.md
├── ROADMAP.md
├── src/
│   ├── main.cpp
│   │
│   ├── core/
│   │   ├── organizer.cpp
│   │   ├── organizer.h
│   │   ├── config.cpp
│   │   ├── config.h
│   │   ├── rules.cpp
│   │   └── rules.h
│   │
│   ├── platform/
│   │   ├── known_folders.cpp
│   │   ├── known_folders.h
│   │   ├── autostart.cpp
│   │   ├── autostart.h
│   │   ├── single_instance.cpp
│   │   ├── single_instance.h
│   │   └── windows_utils.cpp
│   │
│   ├── ui/
│   │   ├── app.cpp
│   │   ├── app.h
│   │   ├── dashboard.cpp
│   │   ├── rules_page.cpp
│   │   ├── history_page.cpp
│   │   └── settings_page.cpp
│   │
│   └── util/
│       ├── logging.cpp
│       ├── logging.h
│       ├── formatting.cpp
│       └── formatting.h
│
├── resources/
└── tests/
```

The exact structure may change if the implementation has a strong technical reason, but the separation of concerns should remain.

---

# Stage 1 — Native C++ Project Skeleton

## Goal

Create the initial C++/CMake project.

## Tasks

* Establish the C++ standard.
* Create `CMakeLists.txt`.
* Create the Windows executable target.
* Create the initial source structure.
* Add a minimal `main.cpp`.
* Add minimal build/logging foundations if useful.
* Confirm the executable builds and launches.

## Do NOT implement

* Organizer engine
* File moving
* JSON configuration
* GUI
* Tray
* Registry
* IPC
* Undo
* History

## Validation

* Configure CMake.
* Build successfully.
* Run the executable.
* Inspect git diff/status.
* Confirm Python source is untouched.

---

# Stage 2 — Configuration System

## Goal

Port JARPISS configuration behavior.

## Implement

* `%APPDATA%\JARPISS`
* `config.json`
* Default configuration
* Default rules
* Configuration loading
* Configuration saving
* Configuration sanitization
* Thread-safe access
* Atomic-ish temporary-file replacement behavior
* History storage
* Statistics storage

## Preserve

* Existing JSON structure
* Existing default values
* Existing rule representation
* Existing history representation where practical
* Existing path token behavior

## Validation

Test:

* First launch
* Existing configuration
* Missing configuration
* Invalid JSON
* Invalid interval
* Invalid rules
* Invalid history
* Save/reload persistence

---

# Stage 3 — Path and Windows Known-Folder Layer

## Goal

Port Windows-specific path behavior.

## Implement

* `{Documents}`
* `{Downloads}`
* `{Music}`
* `{Pictures}`
* `{Videos}`

Use Windows known-folder APIs rather than assuming:

```text
C:\Users\<name>\Pictures
```

This must continue working with redirected or renamed Windows known folders.

## Also port

* Path expansion
* User-home handling
* Path normalization
* Human-readable path formatting where required

## Validation

Compare resolved paths against the Python implementation on the same machine.

---

# Stage 4 — Core Organizer Engine

## Goal

Port the file-organizing engine without any GUI dependency.

The organizer should be independently usable and testable.

## Port

```text
Organizer
├── start()
├── stop()
├── scan_once()
├── background loop
├── stable-file detection
├── extension matching
├── ignored-file handling
├── destination resolution
├── duplicate filename handling
├── file movement
├── statistics
├── history
└── undo
```

## Preserve important behavior

Temporary extensions:

```text
.crdownload
.part
.partial
.tmp
.download
.opdownload
.!ut
```

Ignored names:

```text
desktop.ini
thumbs.db
```

Ignored filename patterns:

```text
~$
.
```

Stable-file detection must preserve the Python implementation's logic.

A file that is still changing must not be moved prematurely.

## Validation

Test:

* PNG
* JPG
* PDF
* ZIP
* Python
* MP4
* Unknown extensions
* Temporary downloads
* Hidden/dot files
* Office lock files
* Directories
* Locked files
* Files changing during scans
* Missing watch directory
* Destination equal to watch directory

---

# Stage 5 — File Movement and Undo Verification

## Goal

Fully verify movement semantics before adding the GUI.

## Verify

### Destination creation

Missing destination folders are automatically created.

### Duplicate names

For:

```text
file.txt
```

if the destination already contains the file:

```text
file (1).txt
file (2).txt
...
```

must be generated.

### History

Each successful move records:

* timestamp
* filename
* source
* destination
* size

### History limit

Only the latest `200` history entries are retained.

### Undo

Undo must:

* verify the destination exists
* recreate the original folder if necessary
* avoid overwriting an existing file
* restore the file
* prevent immediate re-sorting
* update history
* update statistics

---

# Stage 6 — Background Worker and Concurrency

## Goal

Reproduce the Python background-engine behavior safely in C++.

## Implement

* Background scanning
* Stop mechanism
* Wake mechanism
* Scan locking
* Thread-safe configuration access
* Thread-safe event/message communication

The C++ implementation must not perform UI operations directly from the organizer worker thread.

## Validation

Test:

* Start
* Stop
* Start again
* Rapid start/stop
* Configuration changes while scanning
* Manual scan while automatic scanning is active
* Undo while the engine is running

---

# Stage 7 — Windows Single-Instance and IPC

## Goal

Port the Python single-instance mechanism.

The application should prevent multiple JARPISS instances from running simultaneously.

The second launch should communicate with the existing instance instead of opening a second application.

## Preserve behavior

* Primary instance owns the IPC endpoint.
* Secondary instance sends a command.
* Existing instance receives the command.
* Secondary instance exits.

Commands required by the current behavior include:

```text
show
```

Additional commands may be added later only when needed.

## Validation

Launch JARPISS twice.

Expected result:

```text
Instance 1 -> remains running
Instance 2 -> signals instance 1 -> exits
```

---

# Stage 8 — Windows Autostart

## Goal

Port "Start with Windows".

## Implement

Use:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
```

The setting must:

* detect whether autostart is enabled
* enable it
* disable it
* synchronize stale startup commands
* launch JARPISS in background mode

Do not require administrator privileges.

## Validation

* Enable
* Disable
* Restart Windows
* Confirm background startup
* Move the executable/project and verify stale-command handling where applicable

---

# Stage 9 — Native GUI

## Goal

Replace the Python CustomTkinter interface.

The GUI should reproduce the existing functionality, but it does NOT need to reproduce the exact pixel layout of the Python interface.

## Required pages

```text
Dashboard
Rules
History
Settings
```

## Dashboard

Must expose:

* Engine state
* Total files moved
* Total bytes moved
* Session statistics
* Start/Stop
* Scan Now
* Generate Test Files
* Open Folder
* Activity log

## Rules

Must expose:

* Extension
* Destination
* Add rule
* Browse
* Change
* Remove
* Reset/default rules

## History

Must expose:

* Timestamp
* Filename
* Destination
* Undo
* Clear history

## Settings

Must expose:

* Watch folder
* Scan interval
* Start with Windows
* Automatic engine start
* Close to tray
* Tray notifications
* Group by month
* App data folder

---

# Stage 10 — System Tray

## Goal

Port tray behavior.

## Required tray actions

```text
Open JARPISS
Start/Stop Engine
Scan Now
Open Watch Folder
Quit
```

The tray should reflect the current engine state.

When the application is configured to close to tray, pressing the window close button should hide the window instead of terminating the process.

---

# Stage 11 — Background Mode and Notifications

## Goal

Fully reproduce background operation.

Implement:

```text
--background
```

Behavior:

* Start hidden
* Remain active
* Keep organizing
* Remain available through the tray
* Allow the existing instance to be shown
* Send move notifications when enabled and appropriate

The background startup path must not briefly leave a visible window.

---

# Stage 12 — Date Subfolders

## Goal

Port:

```text
Group by month
```

When enabled:

```text
Destination/
└── YYYY-MM/
    └── file.ext
```

Example:

```text
Pictures/
└── Images/
    └── PNG/
        └── 2026-10/
            └── image.png
```

Use the same date semantics as the Python implementation.

---

# Stage 13 — Test File Generator

## Goal

Port the development/testing helper.

It should create representative files in the watch folder:

```text
dummy_doc.docx
script_test.py
pic_test.jpg
```

The exact test contents should remain behaviorally compatible with the Python version unless there is a technical reason otherwise.

---

# Stage 14 — Logging and Error Handling

## Goal

Make error handling production-ready.

Implement:

```text
%APPDATA%\JARPISS\error.log
```

Preserve useful information from the Python version:

* Configuration failures
* Folder access failures
* File movement failures
* Undo failures
* Tray failures
* IPC failures
* Startup failures
* Unexpected exceptions/errors

The application should avoid crashing for ordinary file-system errors.

---

# Stage 15 — Behavioral Regression Suite

## Goal

Compare C++ behavior against Python behavior.

Create automated or semi-automated tests where practical.

## Test matrix

### File types

```text
.png
.jpg
.jpeg
.pdf
.docx
.zip
.py
.cpp
.mp3
.mp4
.exe
.torrent
```

### Special cases

```text
temporary download
unknown extension
duplicate destination
locked source
changing source
missing folder
destination == watch folder
hidden file
desktop.ini
thumbs.db
~$office-file
```

### Application behavior

```text
first launch
config reload
start
stop
restart
manual scan
undo
clear history
autostart
background mode
second instance
tray
notifications
date folders
```

---

# Stage 16 — Final Release Hardening

## Goal

Prepare the C++ version for actual daily use.

Check:

* No debug-only behavior remains.
* No unnecessary console window.
* No accidental Python runtime dependency.
* Configuration survives upgrades.
* Errors are logged.
* Files are never silently overwritten.
* Background mode works.
* Tray works.
* Autostart works.
* Single-instance behavior works.
* Build is reproducible.
* Release executable can be distributed independently.

---

# Completion Criteria

The migration is considered complete only when:

1. The C++ application builds successfully.
2. The C++ application runs without Python.
3. Existing configuration can be loaded or deliberately migrated.
4. Core organizer behavior matches Python.
5. File movement is safe.
6. Duplicate files are never silently overwritten.
7. Undo works.
8. Statistics work.
9. History works.
10. Background operation works.
11. Single-instance behavior works.
12. Windows autostart works.
13. Tray behavior works.
14. GUI functionality is complete.
15. Regression tests pass.
16. The Python implementation remains available as the behavioral reference.

---

# Codex Operating Procedure

For every requested stage:

```text
1. Read ROADMAP.md.
2. Identify the requested stage.
3. Inspect the Python implementation relevant to that stage.
4. Inspect the current C++ implementation.
5. Implement ONLY that stage.
6. Build.
7. Run relevant tests.
8. Inspect git diff/status.
9. Report:
   - files changed
   - behavior implemented
   - tests performed
   - build result
   - known limitations
10. STOP.
```

Never silently advance to the next stage.

---

# Migration Philosophy

JARPISS is being migrated, not reinvented.

The first goal is:

```text
Python behavior
       ↓
faithful C++ implementation
       ↓
verified equivalence
       ↓
future improvements
```

Not:

```text
Python behavior
       ↓
Codex decides it knows better
       ↓
🔥 everything changes 🔥
```

Behavioral improvements can be made later, after the C++ migration is complete and stable.
