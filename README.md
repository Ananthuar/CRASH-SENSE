
---

# CRASH SENSE

**CRASH SENSE** is an AI-powered application crash detection and analysis system designed specifically for Linux environments (Arch Linux, Fedora, etc.). By leveraging machine learning and real-time system monitoring, it identifies application failures, analyzes system metrics during the crash, and provides actionable insights to help developers debug faster.

## 🚀 Features

* **Real-time Monitoring:** Continuously tracks system processes and resource usage using `psutil`.
* **AI-Driven Analysis:** Uses a trained machine learning model to predict crashes based on resource usage patterns (CPU, Memory, Threads), distinguishing between normal behavior and crash precursors.
* **Firebase Authentication:** Secure login and signup flows with email/password authentication using Firebase.
* **Modern Desktop UI:** A clean, dark-themed dashboard built with `CustomTkinter` and `Matplotlib` for visual data tracking, including dynamic resource charts and a speedometer health gauge.
* **Per-Process Detection:** Capable of monitoring multiple applications simultaneously, specifically detecting memory leaks, CPU runaways, thread explosions, zombie processes, and OOM risks.
* **RESTful Backend:** A Flask-based API that acts as a bridge between the system collector and the user interface.

## 📂 Project Structure

```text
CRASH-SENSE/
├── backend/            # Flask API, ML Model, and System Monitor
│   ├── core/           # Process monitor and crash predictor modules
│   ├── train_model.py  # Script for training the crash prediction model
│   ├── firebase_service.py # Firebase interaction logic
│   └── app.py          # Main Flask backend server
├── desktop/            # CustomTkinter GUI application
│   ├── screens/        # Dashboard, Prediction, Login, Signup UI views
│   ├── auth.py         # Client-side authentication handling
│   └── app.py          # Desktop application entry point
├── crash_sense.sh      # Shell script for automated tasks
└── requirements.txt    # Project dependencies
```

## 🛠️ Installation

### Prerequisites

* **Arch Linux** (or any modern Linux distro)
* **Python 3.11+**
* **Tkinter system package** (Required for the GUI)
```bash
sudo pacman -S tk
```

### Setup Environment

1. **Clone the repository:**
```bash
git clone https://github.com/Ananthuar/CRASH-SENSE.git
cd CRASH-SENSE
```

2. **Create and activate a virtual environment:**
```bash
/usr/bin/python -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Firebase Configuration (Required):**
You must place your Firebase Admin SDK credentials file (`firebase-credentials.json`) in the root directory for authentication to function properly.

## 🖥️ Usage

### Quick Start
You can launch both the backend server and the desktop application simultaneously using the shell script:
```bash
./crash_sense.sh
```

### Manual Start

#### 1. Start the Backend
Navigate to the root folder, ensure your `venv` is active, and launch the Flask server:
```bash
python backend/app.py
```
The API will be available at `http://127.0.0.1:5000`.

#### 2. Launch the Desktop Dashboard
In a new terminal (with the `venv` active):
```bash
python desktop/app.py
```

## 📊 API Endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/health` | GET | Returns service status and version. |
| `/api/process-stats` | GET | Returns metrics for all currently tracked processes. |
| `/api/process-alerts` | GET | Returns active process crash precursors and the overall system health score. |

## 🤝 Contributing

This is a team project. To contribute:

1. Create a new branch (`git checkout -b feature/your-feature`).
2. Commit your changes (`git commit -m 'Add some feature'`).
3. Push to the branch (`git push origin feature/your-feature`).
4. Open a Pull Request.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Developed by Ananthu A R and Team.** *Part of the Mini Project in Semester-6 under KTU 2019 Syllabus.*
