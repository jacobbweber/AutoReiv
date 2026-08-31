#!/usr/bin/env bash
# AutoReiv systemd Daemon Installation Script for Ubuntu / Debian
# [REQ-DEPLOY-003]

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: Please run as root (sudo ./install_systemd.sh)"
  exit 1
fi

echo "📦 Installing AutoReiv systemd daemon on $(hostname)..."

# 1. Create dedicated system user & group if missing
if ! id "autoreiv" &>/dev/null; then
  echo "👤 Creating 'autoreiv' system service user..."
  useradd --system --no-create-home --shell /usr/sbin/nologin autoreiv
fi

# 2. Create runtime and storage directories
INSTALL_DIR="/opt/autoreiv"
DATA_DIR="/var/lib/autoreiv/data"
WIKI_DIR="/var/lib/autoreiv/wiki"
CONF_DIR="/etc/autoreiv"

mkdir -p "$INSTALL_DIR" "$DATA_DIR" "$WIKI_DIR" "$CONF_DIR"

# 3. Copy repository files to /opt/autoreiv if run from repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "📂 Syncing AutoReiv codebase into $INSTALL_DIR..."
rsync -a --exclude='.git' --exclude='tests' --exclude='__pycache__' "$REPO_ROOT/" "$INSTALL_DIR/"

# 4. Setup Python Virtual Environment
if [ ! -d "$INSTALL_DIR/.venv" ]; then
  echo "🐍 Initializing Python virtual environment..."
  python3 -m venv "$INSTALL_DIR/.venv"
  "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
  "$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR"
fi

# 5. Set proper permissions
chown -R autoreiv:autoreiv "$INSTALL_DIR" "$DATA_DIR" "$WIKI_DIR" "$CONF_DIR"
chmod 750 "$DATA_DIR" "$WIKI_DIR"

# 6. Install systemd service unit
echo "⚙️  Installing systemd service unit..."
cp "$SCRIPT_DIR/autoreiv.service" /etc/systemd/system/autoreiv.service
systemctl daemon-reload
systemctl enable autoreiv.service
systemctl restart autoreiv.service

echo ""
echo "================================================================="
echo "✅ AutoReiv daemon successfully installed and started!"
echo " • Status  : systemctl status autoreiv.service"
echo " • Logs    : journalctl -u autoreiv.service -f"
echo " • Web UI  : http://localhost:8000"
echo " • Storage : $DATA_DIR and $WIKI_DIR"
echo "================================================================="
