#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  CrashSense Build Script
#  Compiles source into standalone Linux ELF binaries via PyInstaller.
#  Generates a one-click install.sh payload in dist/.
#
#  Usage:
#    ./build.sh              # Full build (daemon + UI)
#    ./build.sh --ui-only    # Rebuild only the CrashSense UI binary
#    ./build.sh --daemon-only # Rebuild only the backend daemon
#    ./build.sh --package    # Full build + create release tarball
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="1.1.3"
BUILD_DAEMON=true
BUILD_UI=true
PACKAGE=false

# ── Argument parsing ─────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --ui-only)     BUILD_DAEMON=false ;;
        --daemon-only) BUILD_UI=false ;;
        --package)     PACKAGE=true ;;
    esac
done

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║    CrashSense Build v${VERSION}          ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

cd "$SCRIPT_DIR"

# ── Step 0: Activate Virtual Environment ─────────────────────────
if [ -d ".venv" ]; then
    echo "[Build] Activating local virtual environment (.venv)..."
    source .venv/bin/activate
else
    echo "[Build] Warning: .venv not found. Using current python environment."
fi

# ── Step 0.5: Verify Dependencies ─────────────────────────────────
echo "[Build] Ensuring dependencies are installed..."
python -m pip install --quiet -r requirements.txt
if ! python -c "import PyInstaller" &>/dev/null; then
    echo "[Build] Installing PyInstaller..."
    python -m pip install --quiet pyinstaller
fi

PYINSTALLER_VER=$(python -c "import PyInstaller; print(PyInstaller.__version__)")
echo "[Build] PyInstaller $PYINSTALLER_VER ready."

# ── Step 1: Compile Backend Daemon ───────────────────────────────
if $BUILD_DAEMON; then
    echo ""
    echo "[Build] Compiling crashsense-daemon..."
    python -m PyInstaller --noconfirm --clean --onefile \
        --exclude-module PyQt5 --exclude-module PySide6 --exclude-module PyQt6 \
        --exclude-module tensorflow --exclude-module keras --exclude-module shap \
        --exclude-module torch --exclude-module cv2 \
        --hidden-import firebase_admin \
        --hidden-import firebase_admin.credentials \
        --hidden-import firebase_admin.auth \
        --hidden-import firebase_admin.firestore \
        --hidden-import sklearn.ensemble \
        --hidden-import sklearn.tree \
        --hidden-import sklearn.utils._cython_blas \
        --hidden-import sklearn.neighbors._partition_nodes \
        --add-data "backend/firebase_service_account.json:." \
        --add-data "backend/models/crash_rf_model.joblib:backend/models/" \
        --noupx \
        --name "crashsense-daemon" \
        backend/app.py
    echo "[Build] crashsense-daemon compiled → dist/crashsense-daemon"
fi

# ── Step 2: Compile Desktop UI ───────────────────────────────────
if $BUILD_UI; then
    echo ""
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
    echo "[Build] CrashSense UI compiled → dist/CrashSense"
fi

# ── Step 3: Generate Installer Script ────────────────────────────
echo ""
echo "[Build] Generating dist/install.sh..."

cat <<'EOF' > dist/install.sh
#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  CrashSense — One-Click Linux Installer
#  Requires: sudo (root) privileges
#  Usage:   sudo ./install.sh
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "[Install] ERROR: Please run as root: sudo ./install.sh"
  exit 1
fi

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/crashsense"

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║  CrashSense — Linux Installer         ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# ── Stop existing service if any ─────────────────────────────────
if systemctl list-unit-files | grep -q crashsense.service; then
    echo "[Install] Stopping existing service..."
    systemctl stop crashsense.service || true
fi

# ── Copy binaries ────────────────────────────────────────────────
echo "[Install] Installing binaries to ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR"
cp "$DIR/crashsense-daemon" "$INSTALL_DIR/"
cp "$DIR/CrashSense"        "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/crashsense-daemon"
chmod +x "$INSTALL_DIR/CrashSense"
echo "[Install] Binaries installed."

# ── Systemd service ──────────────────────────────────────────────
echo "[Install] Configuring systemd service..."
cat <<'SERVICE' > /etc/systemd/system/crashsense.service
[Unit]
Description=CrashSense Engine Daemon
Documentation=https://github.com/your-org/crashsense
After=network.target

[Service]
ExecStart=/opt/crashsense/crashsense-daemon
Restart=on-failure
RestartSec=5
User=root
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable  crashsense.service
systemctl restart crashsense.service

# Wait a moment and verify it started
sleep 2
if systemctl is-active --quiet crashsense.service; then
    echo "[Install] Backend daemon is running."
else
    echo "[Install] WARNING: Backend daemon did not start. Check: journalctl -u crashsense.service -n 30"
fi

# ── Desktop shortcut ─────────────────────────────────────────────
echo "[Install] Creating desktop shortcut..."
mkdir -p /usr/share/applications
cat <<'DESKTOP' > /usr/share/applications/crashsense.desktop
[Desktop Entry]
Name=CrashSense
Comment=AI Crash Prediction & Monitoring Dashboard
Exec=/opt/crashsense/CrashSense
Icon=utilities-system-monitor
Terminal=false
Type=Application
Categories=System;Utility;Monitor;Security;
Keywords=crash;monitor;ai;prediction;
StartupNotify=true
DESKTOP

# Also add a symlink for quick CLI launch
ln -sf "$INSTALL_DIR/CrashSense" /usr/local/bin/crashsense 2>/dev/null || true

echo ""
echo "[Install] ✓ Installation complete!"
echo "  → Backend daemon:  running as crashsense.service"
echo "  → Desktop shortcut: CrashSense in applications menu"
echo "  → Quick launch:    crashsense (from terminal)"
echo "  → Status check:   sudo systemctl status crashsense.service"
echo ""
EOF
chmod +x dist/install.sh
echo "[Build] dist/install.sh generated."

# ── Step 4: Optional packaging ───────────────────────────────────
if $PACKAGE; then
    echo ""
    echo "[Build] Packaging release tarball..."
    TARBALL="CrashSense-Linux-v${VERSION}.tar.gz"

    tar -czf "$TARBALL" \
        -C dist \
        crashsense-daemon \
        CrashSense \
        install.sh

    SIZE=$(du -sh "$TARBALL" | cut -f1)
    echo "[Build] Release tarball: ${TARBALL} (${SIZE})"
fi

echo ""
echo "[Build] ══════════════════════════════════════════"
echo "[Build]  Build complete!"
if $BUILD_DAEMON; then echo "[Build]  dist/crashsense-daemon  ← backend"; fi
if $BUILD_UI;    then echo "[Build]  dist/CrashSense          ← desktop UI"; fi
echo "[Build]  dist/install.sh         ← one-click installer"
echo "[Build] ══════════════════════════════════════════"
echo ""
echo "  To deploy to a target machine:"
echo "  1. rsync dist/ user@target:/tmp/crashsense/"
echo "  2. ssh user@target 'cd /tmp/crashsense && sudo bash install.sh'"
echo ""
