# CSVS IT TECH — Production Deployment Documentation

**Target Domain:** [https://csvsittech.in](https://csvsittech.in)  
**Cloud Infrastructure:** AWS EC2 (`t3.micro`, Region: `ap-south-1` Mumbai)  
**Operating System:** Ubuntu 22.04 / 24.04 LTS  
**Application Stack:** Nginx + Gunicorn + Django 5.2 + PostgreSQL  

---

## 1. Production Architecture Overview

```
Internet
   │
   ▼
GoDaddy DNS (A / CNAME Records)
   │
   ▼
AWS Elastic IP (Port 80 / 443)
   │
   ▼
AWS Security Group (ap-south-1)
   │
   ▼
Nginx (Port 80 -> 301 HTTPS Redirect / Port 443 SSL Termination)
   ├── /static/  ──> /var/www/csvsittech/staticfiles/
   ├── /media/   ──> /var/www/csvsittech/media/
   └── / (Proxy) ──> Unix Domain Socket: /run/gunicorn/csvsittech.sock
                           │
                           ▼
                 Gunicorn Application Server (systemd: csvsittech.service)
                           │
                           ▼
                 Django WSGI Application (vmmc_erp)
                           │
                           ▼
                 PostgreSQL Database (csvsittech_db on 127.0.0.1:5432)
```

---

## 2. DNS Configuration (GoDaddy)

In the GoDaddy DNS Management panel for **`csvsittech.in`**:

1. **Delete** existing parking `A` records (e.g. `3.33.130.190`, `15.197.148.33`).
2. **Add Primary A Record**:
   - **Type:** `A`
   - **Name / Host:** `@`
   - **Value:** `<YOUR_EC2_ELASTIC_IP>`
   - **TTL:** `600 seconds` (or 1/2 hour)
3. **Add CNAME Record**:
   - **Type:** `CNAME`
   - **Name / Host:** `www`
   - **Value:** `csvsittech.in`
   - **TTL:** `1 hour`

---

## 3. AWS EC2 Security Group Configuration

Under the AWS EC2 Management Console for instance **`vmmch`** in region **`ap-south-1`**:

### Inbound Rules:
| Type | Port Range | Protocol | Source | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **HTTP** | 80 | TCP | `0.0.0.0/0`, `::/0` | Let's Encrypt challenge & HTTP->HTTPS redirect |
| **HTTPS** | 443 | TCP | `0.0.0.0/0`, `::/0` | Secure public web traffic |
| **SSH** | 22 | TCP | `<YOUR_IP_ADDRESS>/32` | Administrative SSH access (**Do NOT use 0.0.0.0/0**) |

*Note: Port 5432 (PostgreSQL) must NOT be exposed in the AWS Security Group.*

---

## 4. One-Time EC2 Server Bootstrap

Connect to your EC2 instance via SSH:
```bash
ssh -i /path/to/your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

### Step 1: Clone the repository to `/var/www/csvsittech`
```bash
sudo mkdir -p /var/www/csvsittech
sudo chown ubuntu:ubuntu /var/www/csvsittech
git clone https://github.com/developer-vmmch/csvsittech.git /var/www/csvsittech
cd /var/www/csvsittech
```

### Step 2: Run the automated provisioning script
```bash
sudo bash deploy/scripts/setup_ec2.sh
```
*What this script does:*
* Configures a 2 GB swapfile (prevents OOM on t3.micro).
* Installs PostgreSQL, Nginx, Certbot, Python3-venv, and compilers.
* Sets up UFW firewall (22, 80, 443) and Fail2ban.
* Creates PostgreSQL database (`csvsittech_db`) and user (`csvsittech_user`).
* Generates secure `/etc/csvsittech/.env` with randomized `SECRET_KEY` and DB credentials.
* Creates the Python virtual environment in `/var/www/csvsittech/venv`.

### Step 3: Issue Let's Encrypt SSL Certificate
Ensure your GoDaddy DNS records have propagated to your EC2 IP, then run:
```bash
sudo certbot certonly --webroot -w /var/www/certbot -d csvsittech.in -d www.csvsittech.in
```

### Step 4: Enable Nginx and Systemd Services
```bash
sudo ln -sf /etc/nginx/sites-available/csvsittech.conf /etc/nginx/sites-enabled/csvsittech.conf
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl daemon-reload
sudo systemctl enable --now csvsittech
```

### Step 5: Run First Deployment
```bash
bash deploy/scripts/deploy.sh main
```

---

## 5. GitHub Actions CI/CD Setup

To enable automated zero-downtime deployment whenever a Pull Request is merged into `main`:

### Configure GitHub Repository Secrets
Navigate to: **Settings -> Secrets and variables -> Actions** in your GitHub repository:

1. `EC2_HOST`: The Public IP or Elastic IP of your EC2 instance.
2. `EC2_USER`: `ubuntu`
3. `EC2_SSH_KEY`: The complete private SSH key (contents of the `.pem` file, including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`).
4. `EC2_PORT`: `22` (optional, defaults to 22).

---

## 6. Development & Deployment Workflow

```
1. Create a feature branch locally:
   git checkout -b feature/your-feature-name

2. Develop, test, and commit changes:
   git commit -m "feat: your feature summary"

3. Push feature branch to GitHub:
   git push origin feature/your-feature-name

4. Open a Pull Request targeting 'main' on GitHub.

5. Review & Approve:
   Team / Admin reviews and merges the Pull Request into 'main'.

6. Automated Deployment:
   GitHub Actions automatically connects to EC2, pulls changes, runs migrations, collects static files, restarts Gunicorn, and verifies health.
```

---

## 7. Operational Commands & Maintenance

### Checking Service Status
```bash
# Check Gunicorn service
sudo systemctl status csvsittech

# Check Nginx
sudo systemctl status nginx

# Check PostgreSQL
sudo systemctl status postgresql
```

### Inspecting Logs
```bash
# Gunicorn application logs
tail -f /var/log/gunicorn/error.log
tail -f /var/log/gunicorn/access.log

# Systemd journal logs
sudo journalctl -u csvsittech -f

# Nginx logs
tail -f /var/log/nginx/csvsittech_error.log
tail -f /var/log/nginx/csvsittech_access.log
```

### Running Manual Health Check
```bash
bash /var/www/csvsittech/deploy/scripts/health_check.sh
```

### Rolling Back Deployment
If a broken release was deployed, rollback instantly to the previous commit:
```bash
bash /var/www/csvsittech/deploy/scripts/rollback.sh
```
Or to a specific commit hash:
```bash
bash /var/www/csvsittech/deploy/scripts/rollback.sh <commit-hash>
```
