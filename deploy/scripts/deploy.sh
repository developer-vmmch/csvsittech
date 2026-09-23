#!/usr/bin/env bash
# ============================================================
# CSVS IT TECH — Production Deployment Script
# Executed on EC2 via GitHub Actions or manual trigger
# ============================================================

set -euo pipefail

APP_DIR="/var/www/csvsittech"
VENV_DIR="${APP_DIR}/venv"
BRANCH="${1:-main}"

echo "============================================================"
echo " CSVS IT TECH — Deployment Started ($(date -u '+%Y-%m-%d %H:%M:%S UTC'))"
echo " Target Directory: ${APP_DIR}"
echo " Branch: ${BRANCH}"
echo "============================================================"

cd "${APP_DIR}"

# 1. Fetch & checkout target branch
echo "==> [1/6] Pulling latest changes from Git..."
git fetch origin "${BRANCH}"
git checkout "${BRANCH}"
git pull origin "${BRANCH}"
CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo "Deploying commit: ${CURRENT_COMMIT}"

# 2. Virtual Environment & Dependencies
echo "==> [2/6] Updating Python dependencies..."
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# 3. Database Migrations
echo "==> [3/6] Running Django database migrations..."
python manage.py migrate --noinput

# 4. Collect Static Files
echo "==> [4/6] Collecting static assets..."
python manage.py collectstatic --noinput

# 5. Restart Gunicorn Service
echo "==> [5/6] Restarting application service..."
sudo systemctl restart csvsittech
sleep 3

# Verify Gunicorn is running
if ! systemctl is-active --quiet csvsittech; then
    echo "[ERROR] csvsittech.service failed to start!"
    sudo journalctl -u csvsittech -n 30 --no-pager
    exit 1
fi
echo "csvsittech.service is active and healthy."

# 6. Reload Nginx
echo "==> [6/6] Validating and reloading Nginx..."
sudo nginx -t
sudo systemctl reload nginx

# 7. Run Health Check
echo "==> Running post-deployment health check..."
if [[ -f "${APP_DIR}/deploy/scripts/health_check.sh" ]]; then
    bash "${APP_DIR}/deploy/scripts/health_check.sh"
fi

echo "============================================================"
echo " CSVS IT TECH Deployment SUCCESS! (Commit: ${CURRENT_COMMIT})"
echo " Live at: https://csvsittech.in"
echo "============================================================"
