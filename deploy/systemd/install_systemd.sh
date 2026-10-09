#!/usr/bin/env bash
# AutoReiv systemd Daemon Installation Script for Ubuntu / Debian
# [REQ-DEPLOY-003], [CARD-671]
#
# Usage: sudo ./install_systemd.sh [--prefix DIR] [--data-dir DIR]
#        ./install_systemd.sh [--prefix DIR] [--data-dir DIR] --print-unit   (no root; prints the unit)

set -euo pipefail

DEFAULT_PREFIX="/opt/autoreiv"
DEFAULT_DATA_DIR="/var/lib/autoreiv"
INSTALL_DIR="$DEFAULT_PREFIX"
DATA_ROOT="$DEFAULT_DATA_DIR"
CONF_DIR="/etc/autoreiv"
PRINT_UNIT=false

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

usage() {
  cat <<USAGE
Usage: sudo $0 [--prefix DIR] [--data-dir DIR]
       $0 [--prefix DIR] [--data-dir DIR] --print-unit

  --prefix DIR    Install the app here (default: $DEFAULT_PREFIX)
  --data-dir DIR  AUTOREIV_DATA_DIR for the service (default: $DEFAULT_DATA_DIR)
  --print-unit    Print the rendered systemd unit and exit (no root needed)
  -h, --help      Show this help
USAGE
}

die() { echo "❌ Error: $*" >&2; exit 2; }

abs_path() {
  # $1 = option name, $2 = value. Must be absolute, not "/", no whitespace.
  local v="${2%/}"
  case "$2" in /*) ;; *) die "$1 must be an absolute path (got '$2')";; esac
  [ -n "$v" ] || die "$1 cannot be /"
  [[ "$v" =~ [[:space:]] ]] && die "$1 cannot contain whitespace"
  printf '%s' "$v"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --prefix) [ $# -ge 2 ] || die "--prefix needs a value"; INSTALL_DIR="$(abs_path --prefix "$2")"; shift 2 ;;
    --prefix=*) INSTALL_DIR="$(abs_path --prefix "${1#*=}")"; shift ;;
    --data-dir) [ $# -ge 2 ] || die "--data-dir needs a value"; DATA_ROOT="$(abs_path --data-dir "$2")"; shift 2 ;;
    --data-dir=*) DATA_ROOT="$(abs_path --data-dir "${1#*=}")"; shift ;;
    --print-unit) PRINT_UNIT=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown option '$1'" ;;
  esac
done

# Render the shipped unit (which holds the defaults) for the chosen paths.
render_unit() {
  sed -e "s#${DEFAULT_PREFIX}#${INSTALL_DIR}#g" \
      -e "s#${DEFAULT_DATA_DIR}#${DATA_ROOT}#g" \
      "$SCRIPT_DIR/autoreiv.service"
}

if [ "$PRINT_UNIT" = true ]; then
  render_unit
  exit 0
fi

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
echo " • Prefix   : $INSTALL_DIR"
echo " • Data dir : $DATA_ROOT"
mkdir -p "$INSTALL_DIR" "$DATA_ROOT/database" "$DATA_ROOT/wiki" "$DATA_ROOT/skills" "$CONF_DIR"

# 3. Copy repository files and templates into the install prefix

echo "📂 Syncing AutoReiv codebase, platform agents/skills, and templates into $INSTALL_DIR..."
rsync -a --exclude='.git' --exclude='tests' --exclude='__pycache__' "$REPO_ROOT/" "$INSTALL_DIR/"

# 4. Setup Python Virtual Environment
if [ ! -d "$INSTALL_DIR/.venv" ]; then
  echo "🐍 Initializing Python virtual environment..."
  python3 -m venv "$INSTALL_DIR/.venv"
  "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
  "$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR"
fi

# 5. Set proper permissions
chown -R autoreiv:autoreiv "$INSTALL_DIR" "$DATA_ROOT" "$CONF_DIR"
chmod 750 "$DATA_ROOT"

# 6. Install systemd service unit
echo "⚙️  Installing systemd service unit..."
render_unit > /etc/systemd/system/autoreiv.service
chmod 644 /etc/systemd/system/autoreiv.service
systemctl daemon-reload
systemctl enable autoreiv.service
systemctl restart autoreiv.service

echo ""
echo "================================================================="
echo "✅ AutoReiv daemon successfully installed and started!"
echo " • Status      : systemctl status autoreiv.service"
echo " • Logs        : journalctl -u autoreiv.service -f"
echo " • Web UI      : http://localhost:8000"
echo " • Storage     : $DATA_ROOT"
echo " • Uninstaller : $SCRIPT_DIR/uninstall_systemd.sh (keeps $DATA_ROOT unless --purge-data)"
echo "================================================================="
