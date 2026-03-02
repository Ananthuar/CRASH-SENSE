#!/usr/bin/env bash

# ============================================================================== #
# CrashSense "Smart Installer" for Linux                                          #
# ------------------------------------------------------------------------------ #
# Deploys backend to a systemd service, desktop to the applications menu, and    #
# wraps the logic inside a dedicated Python venv to prevent PEP 668 conflicts.   #
# ============================================================================== #

set -euo pipefail

# 1. Root Check
# This script configures system services and modifies system directories,
# so it needs superuser privileges to work safely.
if [ "$EUID" -ne 0 ]; then
    echo "[Error] Please run this script as root (e.g., sudo ./install.sh)" >&2
    exit 1
fi

echo "================================================================"
echo " Starting CrashSense Smart Installer"
echo "================================================================"

# 2. OS Dependency Resolution
# Detect the OS package manager and install Python 3 and Tkinter system libraries
# (CustomTkinter uses standard tk under the hood, which isn't always installed by default).
echo ""
echo "[1/6] Resolving OS UI Dependencies..."

if command -v pacman > /dev/null; then
    echo "Detected Arch Linux (pacman). Installing python, tk..."
    pacman -Syu --noconfirm python python-pip tk
elif command -v dnf > /dev/null; then
    echo "Detected Fedora/RHEL (dnf). Installing python3, python3-tk..."
    dnf install -y python3 python3-pip python3-tk
elif command -v apt > /dev/null || command -v apt-get > /dev/null; then
    echo "Detected Debian/Ubuntu (apt). Installing python3, python3-venv, python3-tk..."
    apt-get update
    apt-get install -y python3 python3-venv python3-tk python3-pip
else
    echo "[Warning] Unknown package manager. Please ensure Python 3, venv, and Tkinter (tk or python3-tk) are installed."
fi

# 3. Directory Setup
# Copy the raw Python source to an isolated folder in /opt/
echo ""
echo "[2/6] Setting up project directories..."

DEST_DIR="/opt/crashsense"
mkdir -p "$DEST_DIR"

# Get the script's origin directory safely regardless of where it was invoked from
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Copying source files from ${SRC_DIR} to ${DEST_DIR}..."
# Copy backend module
cp -R "${SRC_DIR}/backend" "$DEST_DIR/"
# Copy desktop module
cp -R "${SRC_DIR}/desktop" "$DEST_DIR/"
# Copy python requirements list
cp "${SRC_DIR}/requirements.txt" "$DEST_DIR/"

# 4. Virtual Environment Isolation
# By creating a virtual environment we dodge the "Externally Managed Environment"
# warning seen in PEP 668 in modern Linux distros.
echo ""
echo "[3/6] Creating Python virtual environment..."
python3 -m venv "${DEST_DIR}/venv"

# 5. Python Dependencies
# Use our newly created safe space to install PIP packages
echo ""
echo "[4/6] Installing Python dependencies into isolated venv..."
VENV_PIP="${DEST_DIR}/venv/bin/pip"

# Ensure pip itself is upgraded first
"$VENV_PIP" install --upgrade pip --quiet

# Install standard requirements
echo "Installing from requirements.txt..."
"$VENV_PIP" install -r "${DEST_DIR}/requirements.txt"

# Some UI dependencies might not be in the backend's requirements.txt
echo "Installing UI dependencies..."
"$VENV_PIP" install customtkinter matplotlib numpy plyer pystray pillow --quiet

# 6. Permissions
# We enforce ownership and read-execute privileges for the application files
echo ""
echo "[5/6] Setting correct file permissions..."
chmod -R 755 "$DEST_DIR"
chown -R root:root "$DEST_DIR"

# 7. Systemd Daemon Registration
# Set up a background worker to run our backend (anomaly detection rules)
echo ""
echo "[6/6] Registering systemd daemon & desktop shortcut..."

echo "Generating /etc/systemd/system/crashsense.service..."
cat << 'SERVICE' > /etc/systemd/system/crashsense.service
[Unit]
Description=CrashSense Engine Daemon
After=network.target

[Service]
# We point directly to our virtual environment's Python executable
ExecStart=/opt/crashsense/venv/bin/python /opt/crashsense/backend/app.py
Restart=always
User=root
# Ensure that path calls correctly favour the virtual environment bins
Environment="PATH=/opt/crashsense/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
SERVICE

echo "Reloading systemd, enabling, and starting crashsense.service..."
systemctl daemon-reload
systemctl enable crashsense.service
systemctl restart crashsense.service

# 8. Desktop Shortcut
# Allow users to easily click the app from their Application/Start menus
echo "Generating /usr/share/applications/CrashSense.desktop..."
cat << 'DESKTOP' > /usr/share/applications/CrashSense.desktop
[Desktop Entry]
Name=CrashSense
Comment=AI Crash Prediction Dashboard
Exec=/opt/crashsense/venv/bin/python /opt/crashsense/desktop/app.py
Icon=utilities-system-monitor
Terminal=false
Type=Application
Categories=System;Utility;Security;
DESKTOP

# Final script hygiene: Make sure the destination directories are correctly cached
hash -r || true

echo ""
echo "================================================================"
echo " Installation Complete!"
echo " The background daemon (backend) is now running as a service."
echo " You can launch the CrashSense UI from your applications menu."
echo "================================================================"
