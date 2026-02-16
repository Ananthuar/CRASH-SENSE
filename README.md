
---

# CRASH SENSE

**CRASH SENSE** is an AI-powered application crash detection and analysis system designed specifically for Linux environments (Arch Linux, Fedora, etc.). By leveraging machine learning and real-time system monitoring, it identifies application failures, analyzes system metrics during the crash, and provides actionable insights to help developers debug faster.

## 🚀 Features

* **Real-time Monitoring:** Continuously tracks system processes and resource usage using `psutil`.
* **AI-Driven Analysis:** Uses machine learning to distinguish between intentional process exits and actual software crashes.
* **Modern Desktop UI:** A clean, dark-themed dashboard built with `CustomTkinter` and `Matplotlib` for visual data tracking.
* **RESTful Backend:** A Flask-based API that acts as a bridge between the system collector and the user interface.
* **Cross-Process Detection:** Capable of monitoring multiple applications simultaneously.

## 📂 Project Structure

```text
CRASH-SENSE/
├── backend/            # Flask API and AI Processing logic
│   ├── core/           # System monitoring and data scaling modules
│   └── config.py       # Configuration settings
├── desktop/            # CustomTkinter GUI application
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



## 🖥️ Usage

### 1. Start the Backend

Navigate to the backend folder and launch the Flask server:

```bash
cd backend
python app.py

```

The API will be available at `http://127.0.0.1:5000`. You can check the health status at `/api/health`.

### 2. Launch the Desktop Dashboard

In a new terminal (with the `venv` active):

```bash
cd desktop
python app.py

```

## 📊 API Endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/health` | GET | Returns service status and version. |
| `/api/status` | GET | Returns the current monitoring state. |
| `/api/metrics/current` | GET | Returns real-time CPU/Memory metrics. |

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