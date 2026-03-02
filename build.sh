#!/usr/bin/env bash

# CrashSense Standalone Binary Compilation Script
# Compiles the Python source into standalone ELF binaries using PyInstaller
# Generates a one-click deployment script for Linux VMs.

set -e

echo "[Build] Compiling CrashSense..."

# Install PyInstaller if missing in current environment
if ! python -c "import PyInstaller" &> /dev/null; then
    echo "[Build] Installing PyInstaller in current environment..."
    python -m pip install pyinstaller
fi

# 1. Compile Backend Daemon
echo "[Build] Compiling crashsense-daemon..."
python -m PyInstaller --noconfirm --clean --onefile \
    --exclude-module PyQt5 --exclude-module PySide6 --exclude-module PyQt6 \
    --hidden-import firebase_admin \
    --hidden-import firebase_admin.credentials \
    --hidden-import firebase_admin.auth \
    --hidden-import firebase_admin.firestore \
    --add-data "backend/firebase_service_account.json:." \
    --add-data "backend/models/crash_rf_model.joblib:backend/models/" \
    --name "crashsense-daemon" \
    backend/app.py

# 2. Compile Desktop UI
echo "[Build] Compiling CrashSense UI..."
CTK_PATH=$(python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))")

python -m PyInstaller --noconfirm --clean --onefile --windowed \
    --exclude-module PyQt5 --exclude-module PySide6 --exclude-module PyQt6 \
    --hidden-import PIL._tkinter_finder \
    --add-data "desktop/assets:desktop/assets" \
    --add-data ".env:." \
    --add-data "$CTK_PATH:customtkinter/" \
    --name "CrashSense" \
    desktop/app.py

echo "[Build] Standalone binaries compiled to dist/"

# 3. Generate Target Installer Script
echo "[Build] Generating install.sh payload..."

cat << 'EOF' > dist/install.sh
#!/usr/bin/env bash

# CrashSense Single-Click Target VM Installer
# Must be run as root

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (e.g., sudo ./install.sh)"
  exit 1
fi

echo "[Install] Moving binaries to /opt/crashsense..."
mkdir -p /opt/crashsense

# Ensure we are copying the files correctly regardless of invocation path
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$DIR/crashsense-daemon" /opt/crashsense/
cp "$DIR/CrashSense" /opt/crashsense/
chmod +x /opt/crashsense/crashsense-daemon
chmod +x /opt/crashsense/CrashSense

echo "[Install] Setting up background daemon service..."
cat << 'SERVICE' > /etc/systemd/system/crashsense.service
[Unit]
Description=CrashSense Engine Daemon
After=network.target

[Service]
ExecStart=/opt/crashsense/crashsense-daemon
Restart=always
User=root
# The daemon needs to manage processes and occasionally clear caches
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable crashsense.service
systemctl restart crashsense.service

echo "[Install] Creating Desktop Shortcut..."
mkdir -p /usr/share/applications

# We use a standard system icon fallback
cat << 'DESKTOP' > /usr/share/applications/crashsense.desktop
[Desktop Entry]
Name=CrashSense
Comment=AI Crash Prediction Dashboard
Exec=/opt/crashsense/CrashSense
Icon=utilities-system-monitor
Terminal=false
Type=Application
Categories=System;Utility;Security;
DESKTOP

echo "[Install] Installation complete! The background daemon is running."
echo "You can launch CrashSense from your applications menu or execute /opt/crashsense/CrashSense"
EOF

chmod +x dist/install.sh

echo "[Build] Done! You can now package the 'dist' directory."
