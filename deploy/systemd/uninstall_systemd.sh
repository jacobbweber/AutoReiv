#!/usr/bin/env bash
# AutoReiv systemd Daemon Uninstallation Script for Ubuntu / Debian
# [REQ-DEPLOY-003], [CARD-671]
#
# Usage: sudo ./uninstall_systemd.sh [--prefix DIR] [--data-dir DIR] [--purge-data] [--dry-run]
# Data is kept unless --purge-data is given. Without --prefix/--data-dir the paths are read
# from the installed unit, falling back to the defaults.

set -euo pipefail

DEFAULT_PREFIX="/opt/autoreiv"
DEFAULT_DATA_DIR="/var/lib/autoreiv"
CONF_DIR="/etc/autoreiv"
UNIT_FILE="/etc/systemd/system/autoreiv.service"
INSTALL_DIR=""
DATA_DIR=""
PURGE_DATA=false
DRY_RUN=false

usage() {
  cat <<USAGE
Usage: sudo $0 [--prefix DIR] [--data-dir DIR] [--purge-data] [--dry-run]

  --prefix DIR    App directory to remove (default: from installed unit, else $DEFAULT_PREFIX)
  --data-dir DIR  Data directory (default: from installed unit, else $DEFAULT_DATA_DIR)
  --purge-data    Also delete the data directory and $CONF_DIR (otherwise they are kept)
  --dry-run       Print what would be removed/kept and exit (no root needed)
  -h, --help      Show this help
USAGE
}

die() { echo "❌ Error: $*" >&2; exit 2; }

abs_path() {
  local v="${2%/}"
  case "$2" in /*) ;; *) die "$1 must be an absolute path (got '$2')";; esac
  [ -n "$v" ] || die "$1 cannot be /"
  [[ "$v" =~ [[:space:]] ]] && die "$1 cannot contain whitespace"
  printf '%s' "$v"
}

# Refuse to rm -rf system locations.
check_safe() {
  case "$2" in
    /|/bin|/boot|/dev|/etc|/home|/lib|/lib64|/opt|/proc|/root|/run|/sbin|/srv|/sys|/tmp|/usr|/usr/*|/var|/var/lib)
      die "refusing to use $1 '$2'" ;;
  esac
}

while [ $# -gt 0 ]; do
  case "$1" in
    --prefix) [ $# -ge 2 ] || die "--prefix needs a value"; INSTALL_DIR="$(abs_path --prefix "$2")"; shift 2 ;;
    --prefix=*) INSTALL_DIR="$(abs_path --prefix "${1#*=}")"; shift ;;
    --data-dir) [ $# -ge 2 ] || die "--data-dir needs a value"; DATA_DIR="$(abs_path --data-dir "$2")"; shift 2 ;;
    --data-dir=*) DATA_DIR="$(abs_path --data-dir "${1#*=}")"; shift ;;
    --purge-data) PURGE_DATA=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown option '$1'" ;;
  esac
done

# Fill unset paths from the installed unit, then the defaults.
if [ -f "$UNIT_FILE" ]; then
  if [ -z "$INSTALL_DIR" ]; then
    INSTALL_DIR="$(sed -n 's/^WorkingDirectory=//p' "$UNIT_FILE" | head -n1)"
  fi
  if [ -z "$DATA_DIR" ]; then
    DATA_DIR="$(sed -n 's/^Environment="AUTOREIV_DATA_DIR=\(.*\)"$/\1/p' "$UNIT_FILE" | head -n1)"
  fi
fi
INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_PREFIX}"
DATA_DIR="${DATA_DIR:-$DEFAULT_DATA_DIR}"
check_safe --prefix "$INSTALL_DIR"
check_safe --data-dir "$DATA_DIR"

if [ "$DRY_RUN" = true ]; then
  echo "Dry run (nothing changed):"
  echo " • stop/disable autoreiv.service and remove $UNIT_FILE"
  echo " • remove $INSTALL_DIR"
  if [ "$PURGE_DATA" = true ]; then
    echo " • remove $DATA_DIR"
    echo " • remove $CONF_DIR"
  else
    echo " • keep $DATA_DIR"
    echo " • keep $CONF_DIR"
  fi
  exit 0
fi

if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: Please run as root (sudo ./uninstall_systemd.sh [--purge-data])"
  exit 1
fi

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
if [ -f "$UNIT_FILE" ]; then
  echo "🗑️  Removing systemd service unit file..."
  rm -f "$UNIT_FILE"
  systemctl daemon-reload
  systemctl reset-failed || true
fi

# 3. Remove application directory
if [ -d "$INSTALL_DIR" ]; then
  echo "📂 Removing application directory ($INSTALL_DIR)..."
  rm -rf "$INSTALL_DIR"
fi

# 4. Handle persistent user data and configuration
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
