#!/usr/bin/env bash
# ============================================================
# CSVS IT TECH — EC2 Server Provisioning & Setup Script
# Target: Ubuntu 22.04 / 24.04 LTS on AWS EC2 (t3.micro)
# ============================================================

set -euo pipefail

echo "============================================================"
echo " Starting CSVS IT TECH EC2 Provisioning"
echo "============================================================"

# Ensure script is run as root or with sudo
if [[ $EUID -ne 0 ]]; then
   echo "[ERROR] This script must be run as root (use sudo)." 
   exit 1
fi

APP_USER="ubuntu"
APP_DIR="/var/www/csvsittech"
CONF_DIR="/etc/csvsittech"
LOG_DIR="/var/log/gunicorn"
DB_NAME="csvsittech_db"
DB_USER="csvsittech_user"

# ------------------------------------------------------------
# 1. System Update & Dependencies
# ------------------------------------------------------------
echo "==> [1/8] Updating package repository and installing packages..."
apt update -y
DEBIAN_FRONTEND=noninteractive apt upgrade -y

DEBIAN_FRONTEND=noninteractive apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    postgresql \
    postgresql-contrib \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    curl \
    git \
    htop \
    fail2ban

# ------------------------------------------------------------
# 2. Swapfile Setup (Essential for t3.micro 1GB RAM)
# ------------------------------------------------------------
echo "==> [2/8] Checking & configuring 2GB swap space..."
if ! swapon --show | grep -q "/swapfile"; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    if ! grep -q "/swapfile" /etc/fstab; then
        echo "/swapfile none swap sw 0 0" >> /etc/fstab
    fi
    sysctl vm.swappiness=10
    if ! grep -q "vm.swappiness" /etc/sysctl.conf; then
        echo "vm.swappiness=10" >> /etc/sysctl.conf
    fi
    echo "Swapfile (2GB) created and activated."
else
    echo "Swapfile already active."
fi

# ------------------------------------------------------------
# 3. Security & Firewall Configuration (UFW)
# ------------------------------------------------------------
echo "==> [3/8] Configuring UFW Firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable

systemctl enable fail2ban
systemctl start fail2ban

# ------------------------------------------------------------
# 4. PostgreSQL Configuration
# ------------------------------------------------------------
echo "==> [4/8] Configuring PostgreSQL Database..."
systemctl start postgresql
systemctl enable postgresql

DB_PASSWORD="${DB_PASSWORD:-}"
if [[ -z "$DB_PASSWORD" ]]; then
    DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 20)
    echo "Generated secure PostgreSQL password for ${DB_USER}: ${DB_PASSWORD}"
fi

# Create database and user if not exists
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
sudo -u postgres psql -d ${DB_NAME} -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"

# ------------------------------------------------------------
# 5. Project Directories & Permissions
# ------------------------------------------------------------
echo "==> [5/8] Creating Application Directories..."
mkdir -p "${APP_DIR}"
mkdir -p "${APP_DIR}/staticfiles"
mkdir -p "${APP_DIR}/media"
mkdir -p "${CONF_DIR}"
mkdir -p "${LOG_DIR}"
mkdir -p "/var/www/certbot"
mkdir -p "/run/gunicorn"

chown -R "${APP_USER}:www-data" "${APP_DIR}"
chown -R "${APP_USER}:www-data" "${LOG_DIR}"
chown -R "${APP_USER}:www-data" "/run/gunicorn"
chown -R www-data:www-data "/var/www/certbot"
chmod -R 775 "${APP_DIR}/staticfiles"
chmod -R 775 "${APP_DIR}/media"
chmod -R 775 "${LOG_DIR}"
chmod 755 "/var/www/certbot"

# ------------------------------------------------------------
# 6. Production Environment File (/etc/csvsittech/.env)
# ------------------------------------------------------------
echo "==> [6/8] Generating Production Environment Configuration..."
ENV_FILE="${CONF_DIR}/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    DJANGO_SECRET=$(openssl rand -base64 48 | tr -dc 'a-zA-Z0-9!@#$%^&*(-_=+)' | head -c 50)
    cat << ENV_EOF > "$ENV_FILE"
# CSVS IT TECH Production Environment
DEBUG=False
SECRET_KEY=${DJANGO_SECRET}
ALLOWED_HOSTS=csvsittech.in,www.csvsittech.in,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://csvsittech.in,https://www.csvsittech.in
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000

USE_POSTGRES=True
DB_ENGINE=django.db.backends.postgresql
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=127.0.0.1
DB_PORT=5432
ENV_EOF
    chmod 600 "$ENV_FILE"
    chown "${APP_USER}:www-data" "$ENV_FILE"
    echo "Created ${ENV_FILE} with secure permissions."
else
    echo "${ENV_FILE} already exists. Preserving current configuration."
fi

# ------------------------------------------------------------
# 7. Virtual Environment Setup
# ------------------------------------------------------------
echo "==> [7/8] Initializing Python Virtual Environment..."
if [[ ! -d "${APP_DIR}/venv" ]]; then
    sudo -u "${APP_USER}" python3 -m venv "${APP_DIR}/venv"
    sudo -u "${APP_USER}" "${APP_DIR}/venv/bin/pip" install --upgrade pip setuptools wheel
fi

# ------------------------------------------------------------
# 8. Linking Services
# ------------------------------------------------------------
echo "==> [8/8] Linking Nginx & Systemd Service..."
if [[ -f "${APP_DIR}/deploy/systemd/csvsittech.service" ]]; then
    cp "${APP_DIR}/deploy/systemd/csvsittech.service" /etc/systemd/system/csvsittech.service
    systemctl daemon-reload
    systemctl enable csvsittech
fi

if [[ -f "${APP_DIR}/deploy/nginx/csvsittech.conf" ]]; then
    cp "${APP_DIR}/deploy/nginx/csvsittech.conf" /etc/nginx/sites-available/csvsittech.conf
    # Remove default Nginx site
    rm -f /etc/nginx/sites-enabled/default
fi

echo "============================================================"
echo " EC2 Provisioning Complete!"
echo " Next Steps:"
echo " 1. Clone repository to ${APP_DIR} (if not already present)"
echo " 2. Run Certbot to acquire SSL certificate:"
echo "    certbot certonly --webroot -w /var/www/certbot -d csvsittech.in -d www.csvsittech.in"
echo " 3. Enable Nginx site: ln -sf /etc/nginx/sites-available/csvsittech.conf /etc/nginx/sites-enabled/"
echo " 4. Run ${APP_DIR}/deploy/scripts/deploy.sh"
echo "============================================================"
