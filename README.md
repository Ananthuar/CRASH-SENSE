
---

# 🛡️ CRASH SENSE (v1.1.1)
### *AI-Powered Predictive Resolution Engine for Linux*

**CRASH SENSE** is a next-generation, self-healing application monitoring system engineered for bare-metal Linux environments (Arch Linux, Fedora, etc.). Unlike traditional monitors that simply log failures, CrashSense utilizes a **Hybrid Edge AI Architecture** to predict application instability and neutralize threats in real-time before they escalate into system-wide crashes.

---

## 🚀 The Edge AI Revolution (v1.1.1)

Version 1.1.1 marks the transition from a passive monitoring tool to an **Active Resolution Engine**. By moving inference to the Edge, CrashSense provides sub-millisecond response times to system anomalies.

### 🧠 Automated System Resolution
When the ML model identifies a crash precursor, the `SystemResolver` daemon triggers a tiered intervention protocol:

* **Tier 1: Dynamic Throttling (`renice`)** - Automatically deprioritizes CPU-bound processes to restore system responsiveness.
* **Tier 2: Memory Relief (`drop_caches`)** - Triggers kernel-level cache clearing when OOM (Out of Memory) conditions are predicted with >75% probability.
* **Tier 3: Graceful Neutralization (`SIGTERM`)** - Sanitizes the environment by terminating runaway threads or leaking memory blocks before they trigger a kernel panic.

### 🔔 Intelligence-Driven Notifications
* **Context-Aware Toasts:** Fluid, color-coded animations provide non-blocking status updates for "Healthy," "At-Risk," and "Resolved" states.
* **Native OS Bridge:** Utilizes `dbus` and `notify-send` to dispatch high-priority system alerts if the main UI is minimized or running in the system tray.

---

## 📂 Project Architecture & SDLC Documentation

CrashSense was developed following a rigorous **Software Development Life Cycle (SDLC)**. Detailed technical blueprints are available in the `docs/` directory:

| Document | Purpose |
| :--- | :--- |
| 📘 **[Developer Guide](./docs/DEVELOPER_GUIDE.md)** | Deep dive into the codebase, API structure, and environment scaling. |
| 📜 **[SRS Document](./docs/_Crash_Sense_SRS_Version1.1_.pdf)** | Full functional/non-functional requirements and user personas. |
| 📐 **[SDD Document](./docs/_Crash_Sense_SDD_Version1.1_.pdf)** | System design blueprints, module interaction diagrams, and logic flows. |

---

## 🔬 Machine Learning Technical Stack

Our predictive engine is trained on high-dimensional system telemetry:

* **Model:** Random Forest Classifier optimized for low-latency inference.
* **Telemetry:** Real-time tracking of CPU affinity, RSS/VMS memory trends, and thread parent-child hierarchy.
* **Backend:** Flask-based RESTful API serving as the neural bridge between the daemon and UI.
* **Frontend:** CustomTkinter dark-themed dashboard with Matplotlib integration for real-time data visualization.

---

## 🛠️ Portable Deployment & Execution

CrashSense is now distributed as a **Zero-Install Portable Application** for Linux. No Python configuration, installation scripts, or root (`sudo`) privileges are required on the target machine. The UI seamlessly manages the background daemon lifecycle automatically.

### 1. Download & Extract
Download the latest `CrashSense-Linux-v1.1.1.tar.gz` from our [Releases](https://github.com/Ananthuar/CRASH-SENSE/releases) page.
```bash
tar -xzvf CrashSense-Linux-v1.1.1.tar.gz

```

### 2. Run the Application

Navigate into the extracted folder and simply execute the main binary.

```bash
cd dist
./CrashSense

```

*(Note: If the application does not launch immediately, ensure it has execution permissions by running `chmod +x CrashSense` first.)*

---

## 👥 Meet the Team

Developed with passion by **Ananthu A R and Team**.

* **Institution:** College of Engineering and Management Punnapra
* **Academic Focus:** Semester-6 | Computer Science and Engineering
* **Syllabus:** APJ Abdul Kalam Technological University (KTU) 2019 Scheme

---

**License:** Distributed under the MIT License. See `LICENSE` for more information.

---