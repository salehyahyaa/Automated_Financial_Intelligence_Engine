#!/usr/bin/env bash
# Run on the EC2 host after the repo is at INSTALL_ROOT (git clone or rsync).
#
# One-time host prep (Amazon Linux 2023 example):
#   sudo dnf install -y git python3.11
#   git clone <your-repo-url> ~/FinancialProject
#   cd ~/FinancialProject && ./deploy/ec2-bootstrap.sh
# (numpy 2.3.x and current pins need Python >= 3.11; default "python3" on AL2023 is often 3.9.)
# Copy .env to repo root, then follow the printed systemd commands. Open SG TCP 8001.
#
# Usage: ./deploy/ec2-bootstrap.sh [INSTALL_ROOT]
# Optional: export SERVICE_USER=ubuntu  (defaults: current user, or SUDO_USER if root)
set -euo pipefail

INSTALL_ROOT="${1:-$HOME/FinancialProject}"
if [[ -n "${SERVICE_USER:-}" ]]; then
  :
elif [[ "$(id -un)" == "root" ]]; then
  SERVICE_USER="${SUDO_USER:-ubuntu}"
else
  SERVICE_USER="$(id -un)"
fi

cd "$INSTALL_ROOT"
PYTHON_BIN=""
for c in python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    PYTHON_BIN="$c"
    break
  fi
done
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Need Python >= 3.11 (see requirements.txt). Example: sudo dnf install -y python3.11" >&2
  exit 1
fi
echo "Using: $PYTHON_BIN ($($PYTHON_BIN --version))"
"$PYTHON_BIN" -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

UNIT_PATH="/etc/systemd/system/financial-engine-api.service"
TMP_UNIT="$(mktemp)"
sed -e "s|@INSTALL_ROOT@|${INSTALL_ROOT}|g" -e "s|@SERVICE_USER@|${SERVICE_USER}|g" \
  "$INSTALL_ROOT/deploy/financial-engine-api.service.template" >"$TMP_UNIT"

echo ""
echo "Python deps installed. Next:"
echo "  1. Copy your production .env to: ${INSTALL_ROOT}/.env"
echo "     Set at least: HOST=0.0.0.0 (optional; systemd already binds 0.0.0.0),"
echo "     CORS_ALLOW_ORIGINS to your dashboard origin(s)."
echo "  2. Install and start systemd (Amazon Linux / RHEL-like):"
echo "       sudo cp ${TMP_UNIT} ${UNIT_PATH}"
echo "       sudo systemctl daemon-reload"
echo "       sudo systemctl enable --now financial-engine-api"
echo "       curl -sS http://127.0.0.1:8001/health"
echo ""
echo "Generated unit file (review, then sudo cp to ${UNIT_PATH}):"
echo "---"
cat "$TMP_UNIT"
echo "---"
echo "Temp file: $TMP_UNIT (delete after sudo cp if you like)"
