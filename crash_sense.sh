#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  CrashSense — Universal Linux Launcher
# ═══════════════════════════════════════════════════════════════
#
#  This script prepares the environment and launches the CrashSense
#  desktop application on any Linux distribution with Python 3.8+.
#
#  What it does:
#    1. Verifies Python 3 and pip are available.
#    2. Creates a virtual environment (if one doesn't already exist).
#    3. Installs all Python dependencies.
#    4. Launches the CustomTkinter desktop application.
#
#  Prerequisites:
#    - Python 3.8+ with pip
#    - A display server (X11 or Wayland)
#    - libffi, libtk (usually pre-installed)
#
#  Usage:
#    chmod +x crash_sense.sh
#    ./crash_sense.sh
#
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ── Constants ───────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
REQ_FILE="${SCRIPT_DIR}/requirements.txt"
APP_MODULE="desktop.app"

# ── Colours for terminal output ─────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'  # No Colour

# ── Helper Functions ────────────────────────────────────────────
info()  { echo -e "${GREEN}[CrashSense]${NC} $*"; }
warn()  { echo -e "${YELLOW}[CrashSense]${NC} $*"; }
error() { echo -e "${RED}[CrashSense]${NC} $*" >&2; }

# ── Step 1: Check Python 3 ─────────────────────────────────────
info "Checking for Python 3..."

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" --version 2>&1 | grep -oP '\d+\.\d+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [[ "$major" -ge 3 ]] && [[ "$minor" -ge 8 ]]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    error "Python 3.8+ is required but not found."
    error "Install it using your package manager:"
    error "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    error "  Arch/Manjaro:  sudo pacman -S python python-pip"
    error "  Fedora:        sudo dnf install python3 python3-pip"
    exit 1
fi
info "Found $($PYTHON --version)"

# ── Step 2: Create Virtual Environment ─────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
    info "Virtual environment created at ${VENV_DIR}"
fi

# Activate the virtual environment
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
info "Virtual environment activated."

# ── Step 3: Install Dependencies ───────────────────────────────
if [[ -f "$REQ_FILE" ]]; then
    info "Installing dependencies from requirements.txt..."
    pip install --quiet --upgrade pip
    pip install --quiet -r "$REQ_FILE"
    # Install desktop-specific dependencies not in requirements.txt
    pip install --quiet customtkinter matplotlib numpy
    info "All dependencies installed."
else
    warn "requirements.txt not found at ${REQ_FILE}. Skipping dependency install."
    warn "Installing minimum desktop dependencies..."
    pip install --quiet customtkinter matplotlib numpy
fi

# ── Step 4: Launch the Application ─────────────────────────────
info "Starting CrashSense Desktop Application..."
echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║     🛡  CRASH SENSE v1.0              ║"
echo "  ║     AI-Based Crash Detection System   ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

cd "$SCRIPT_DIR"
"$PYTHON" -m "$APP_MODULE"

# ── Cleanup on Exit ─────────────────────────────────────────────
info "Application closed. Goodbye!"
