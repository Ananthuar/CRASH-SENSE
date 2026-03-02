# CrashSense: The Comprehensive Developer Guide

Welcome to the definitive backend-to-frontend developer guide for **CrashSense v1.1.1**. This document is designed for junior-to-intermediate Python developers, giving you a full structural breakdown of the application from its initial skeleton to the advanced deployment setups added today. By reading this guide, you will understand exactly how the entire system works under the hood.

---

## 📖 Chapter 1: The Core Architecture Concept

CrashSense is an **AI-driven System Monitor**. It automatically watches the processes running on a Linux machine, predicts when they are about to crash using a Machine Learning model, automatically mitigates those crashes (like killing a runaway process), and provides a beautiful desktop dashboard.

The project is split into two massive pillars:
1. **The Backend Daemon (`backend/`)**: A headless (no-UI) Python Flask engine running quietly in the background on port 5000. It reads CPU/Memory stats and feeds them through the AI.
2. **The Desktop UI (`desktop/`)**: A rich, dark-mode window built using `customtkinter`. It doesn't actually read system stats directly—instead, it asks the Backend Daemon for data via HTTP requests and displays it prettily.

To make the app easy for users, the Desktop UI acts as the master. When the user opens the Desktop app, it invisibly starts the Backend engine at the same time.

---

## 🧠 Chapter 2: The Backend Daemon (`backend/`)

Let's look at the engine. The background worker operates in a tight loop and runs a lightweight `Flask` REST API server.

### 2.1 The System Collector (`backend/core/collector.py`)
This file is the eyes and ears of the app. It uses the `psutil` (Process and System Utilities) library to scrape the operating system.
- It loops through every single Process ID (PID) running on Linux.
- It grabs the `cpu_percent()`, memory usage (`rss` resident set size), `num_threads()`, and open file descriptors.
- It bundles this massive list of dictionaries and hands it to the Machine Learning Engine.

### 2.2 The ML Predictor (`backend/core/ml_engine.py`)
Earlier in the project lifecycle, we trained a Random Forest classification model (`crash_rf_model.joblib`) on thousands of historical crash profiles using `scikit-learn`.
- The engine loads this `.joblib` binary file.
- It injects the live metrics produced by the collector into the model.
- The model outputs a probability: e.g., `"Process 4022 (Chrome) has an 82% chance of crashing due to a threading explosion."`
- The engine tags these processes and creates "Alerts" inside an SQLite database.

### 2.3 Automated Resolutions (`backend/core/resolutions.py`)
If a process is going to crash aggressively and freeze the user's computer, CrashSense will kill it or throttle it.
- **Terminate**: If a process crosses the 95% critical threshold, `psutil.Process(pid).terminate()` is called. 
- **Throttle**: If it's acting up but not deadly, we change the Linux `"niceness"` using `process.nice(19)`, stripping away its CPU priority so it stops lagging the computer.

### 2.4 The Flask API (`backend/app.py` & `routes/`)
All of this data is locked inside the background algorithm. To expose it, we built a Flask web server on `http://127.0.0.1:5000`. 
- Our UI makes standard web requests (`requests.get("http://127.0.0.1:5000/api/dashboard")`) to get JSON payloads containing the active alerts, system health score, and logs.

---

## 🖥️ Chapter 3: The CustomTkinter UI (`desktop/`)

The Graphical User Interface (GUI) is completely decoupled from the ML engine. It relies strictly on `customtkinter` to draw widgets natively.

### 3.1 The Main App Class (`desktop/app.py`)
This is the master entry point when the user clicks the application (`class CrashSenseApp(ctk.CTk)`).
- It generates the root window `1280x800`.
- Instead of keeping 10 screens consuming RAM at once, we built a **lazy-loading router**. When the user clicks "Settings" on the sidebar, the `_navigate()` method explicitly destroys the old screen widget and builds the new `SettingsScreen` from scratch.

### 3.2 Firebase Auth (`desktop/auth.py`)
CrashSense supports user profiles. But instead of storing passwords in our local SQLite database (which is dangerous), we wired the UI directly to Google's Firebase servers.
- **Email/Password Logging:** It uses the Firebase REST API (`identitytoolkit.googleapis.com`) directly. It crafts a JSON payload with the user's email and password, sends it to Google, and gets back an `id_token`. We do not use the bulky `firebase-admin` python library on the UI because it breaks easily in compiled desktop apps.
- **Google OAuth:** For "Sign in with Google", Python cannot natively render a modern Google login screen securely. So `desktop/auth.py` dynamically spins up a temporary mini-webserver on port `5557`, pops open the user's default browser (Chrome/Firefox) to Google's login page, and waits for Google to bounce a secure token back to the mini-server when unquestioned. It then closes the browser tab!

### 3.3 Dynamic Screen Errors (The Update)
Originally, if the backend Flask server died, the UI screens would freeze or print raw Python exception stack traces directly into the UI.
We wrapped everything in `try/except` blocks.
```python
        try:
            resp = requests.get(f"http://127.0.0.1:5000/api/users", timeout=3)
        except requests.exceptions.ConnectionError:
            # Safe Fallback! The server is missing!
            display_label("Backend offline")
```
Now, if the backend goes down, the UI handles it smoothly, displaying elegant "Offline" labels instead of crashing.

---

## 🔔 Chapter 4: System Integrations

### 4.1 Background Tray Icon (`desktop/tray.py`)
A monitoring app shouldn't close when you hit the "X" button; it should minimize.
Using the `pystray` library, we generate an icon in the Linux top-bar/corner. The `CrashSenseApp` intercepts the `WM_DELETE_WINDOW` protocol (the mathematical "close" button signal) and runs `self.withdraw()` instead of `self.quit()`. The window vanishes, but the Python script keeps running!

### 4.2 Linux Notifications (`desktop/components/notification_toast.py`)
When the AI kills a runaway app, we want to tell the user immediately.
- We first attempt to run the standard Linux command: `subprocess.run(["notify-send", "-u", "critical", "CrashSense", "Threat Neutralized!"])`. This generates standard OS popups.
- If they don't have a notification daemon, our custom `NotificationToast` widget slides beautifully up from the bottom-right corner of the CustomTkinter window using geometry animations.

---

## 📦 Chapter 5: Deployment & Packaging

A major milestone of this project was moving from "a bunch of Python scripts" into a **standalone, portable Linux Application** that a normal user can just double-click.

### 5.1 PyInstaller (`build.sh`)
We use PyInstaller to freeze all our `.py` code into a single, compiled `.bin` executable file.
- `pyinstaller --onefile --add-data ".env:." desktop/app.py`
The `--add-data` flag is crucial. By default, PyInstaller throws away `.env` config files and `.png` images. We force it to zip those static assets INSIDE the binary file.

### 5.2 The Temporary Extraction Problem
When you run a compiled PyInstaller app, it actually unzips its inner contents into a secret temporary folder in your system's `/tmp` directory, named something like `_MEIPASS/`. 
If our code said `open("../assets/icon.png")`, it would fail, because the structure inside `/tmp` doesn't match our GitHub project structure.

**The Solution:**
```python
def get_asset_path(relative_path):
    try:
        base_path = sys._MEIPASS # Are we running as a compiled app? Great, look in the temp folder!
    except Exception:
        base_path = os.path.dirname(...) # Are we running from source code? Look relative to the script!
    return os.path.join(base_path, relative_path)
```
This single function solved the `FileNotFoundError` bug that plagued our initial compiled versions.

---

## 🔌 Chapter 6: The "Invisibly Integrated" Masterpiece

Today, we made the final adjustments to make CrashSense feel like a professionally engineered System App, rather than a Python script.

### 6.1 Backend Process Autostart
Originally, users had to run a heavy Linux `install.sh` script using `sudo` to configure systemd background workers to run the Flask API. We hate that.
We made the UI (frontend) act as the manager.
In `desktop/app.py` `__init__`, we find the path of the UI binary (`os.path.dirname(sys.executable)`). We look for the `crashsense-daemon` binary sitting right next to it, and we run `subprocess.Popen([daemon])`. 
- **Result:** When the user double-clicks the UI icon, the AI brain spins up invisibly in the background.

### 6.2 Graceful Shutdown Intercepts
If the UI crashes, we don't want the invisible daemon lingering in RAM forever (a "zombie process").
In `desktop/app.py`, we import `signal`.
```python
    import signal
    def handle_signal(sig, frame):
        app._daemon_process.terminate()
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
```
If the OS attempts to forcefully kill the UI (`SIGTERM`) or the user mashes `CTRL+C` (`SIGINT`), our little handler function grabs the wheel for a split second, issues a kill command to the background daemon, and then lets the UI die cleanly. 

### 6.3 Self-Registering `.desktop` Shortcut (`desktop/linux_integration.py`)
Lastly, users expect apps to appear in their GNOME or KDE Application Menus.
We implemented `create_desktop_shortcut()` which runs the very first time the user launches the app:
1. It copies the `icon.png` permanently to the Linux `~/.local/share/icons/` folder.
2. It generates a literal `CrashSense.desktop` text file and puts it in `~/.local/share/applications/`.
3. It sets `os.chmod()` to give it executable permissions.

- **Result:** The moment a user runs the app from their downloads folder, CrashSense seamlessly hooks itself into the Linux OS, allowing them to search "CrashSense" in their Start Menu forever after.

***

**End of Developer Guide.**  
*By following this architecture, a standard Python developer can confidently navigate, expand, or debug CrashSense.*
