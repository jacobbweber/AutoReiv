#!/usr/bin/env bash
# AutoReiv systemd Daemon Uninstallation Script for Ubuntu / Debian
# [REQ-DEPLOY-003]

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: Please run as root (sudo ./uninstall_systemd.sh [--purge-data])"
  exit 1
fi

PURGE_DATA=false
for arg in "$@"; do
  case "$arg" in
    --purge-data)
      PURGE_DATA=true
      shift
      ;;
    *)
      ;;
  esac
done

echo "🛑 Uninstalling AutoReiv systemd daemon on $(hostname)..."

# 1. Stop and disable systemd service
if systemctl is-active --quiet autoreiv.service 2>/dev/null; then
  echo "⏹️  Stopping autoreiv.service..."
  systemctl stop autoreiv.service || true
fi

if systemctl is-enabled --quiet autoreiv.service 2>/dev/null; then
  echo "🔌 Disabling autoreiv.service..."
  systemctl disable autoreiv.service || true
fi

# 2. Remove systemd service unit definition
if [ -f /etc/systemd/system/autoreiv.service ]; then
  echo "🗑️  Removing systemd service unit file..."
  rm -f /etc/systemd/system/autoreiv.service
  systemctl daemon-reload
  systemctl reset-failed || true
fi

# 3. Remove application directory
INSTALL_DIR="/opt/autoreiv"
if [ -d "$INSTALL_DIR" ]; then
  echo "📂 Removing application directory ($INSTALL_DIR)..."
  rm -rf "$INSTALL_DIR"
fi

# 4. Handle persistent user data and configuration
DATA_DIR="/var/lib/autoreiv"
CONF_DIR="/etc/autoreiv"

if [ "$PURGE_DATA" = true ]; then
  echo "⚠️  Purging all persistent user data and configuration as requested..."
  rm -rf "$DATA_DIR" "$CONF_DIR"
  echo "✅ Persistent data removed."
else
  echo "🔒 Keeping user data and configuration safe:"
  echo " • Data     : $DATA_DIR"
  echo " • Config   : $CONF_DIR"
  echo " (To permanently remove data as well, run with: sudo ./uninstall_systemd.sh --purge-data)"
fi

echo ""
echo "================================================================="
echo "✅ AutoReiv daemon successfully uninstalled!"
echo "================================================================="
