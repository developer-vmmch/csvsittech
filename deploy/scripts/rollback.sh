#!/usr/bin/env bash
# ============================================================
# CSVS IT TECH — Production Rollback Script
# Usage: ./rollback.sh [optional_target_commit_or_tag]
# ============================================================

set -euo pipefail

APP_DIR="/var/www/csvsittech"
VENV_DIR="${APP_DIR}/venv"
TARGET_COMMIT="${1:-HEAD~1}"

echo "============================================================"
echo " Starting Rollback for CSVS IT TECH"
echo " Target Commit: ${TARGET_COMMIT}"
echo "============================================================"

cd "${APP_DIR}"

CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo "Current commit before rollback: ${CURRENT_COMMIT}"

# 1. Rollback code
echo "==> Reverting Git repository to ${TARGET_COMMIT}..."
git checkout "${TARGET_COMMIT}"
NEW_COMMIT=$(git rev-parse --short HEAD)
echo "Now on commit: ${NEW_COMMIT}"

# 2. Re-install Python dependencies for that commit
echo "==> Restoring dependencies..."
source "${VENV_DIR}/bin/activate"
pip install -r requirements.txt

# 3. Database check / collectstatic
echo "==> Re-collecting static files..."
python manage.py collectstatic --noinput

# 4. Restart Services
echo "==> Restarting Gunicorn & Nginx..."
sudo systemctl restart csvsittech
sudo systemctl reload nginx

# 5. Health Check
echo "==> Verifying rollback state..."
if [[ -f "${APP_DIR}/deploy/scripts/health_check.sh" ]]; then
    bash "${APP_DIR}/deploy/scripts/health_check.sh"
fi

echo "============================================================"
echo " Rollback Complete! Current Active Commit: ${NEW_COMMIT}"
echo "============================================================"
