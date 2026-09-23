#!/usr/bin/env bash
# ============================================================
# CSVS IT TECH — Production Health Check Script
# ============================================================

set -euo pipefail

SOCKET="/run/gunicorn/csvsittech.sock"
FAILURES=0

echo "--- Performing System Health Checks ---"

# Check PostgreSQL
if systemctl is-active --quiet postgresql; then
    echo " [OK] PostgreSQL service is running."
else
    echo " [FAIL] PostgreSQL service is down!"
    FAILURES=$((FAILURES + 1))
fi

# Check Gunicorn Service
if systemctl is-active --quiet csvsittech; then
    echo " [OK] Gunicorn (csvsittech) service is running."
else
    echo " [FAIL] Gunicorn (csvsittech) service is down!"
    FAILURES=$((FAILURES + 1))
fi

# Check Gunicorn Socket
if [[ -S "$SOCKET" ]]; then
    echo " [OK] Gunicorn socket file exists ($SOCKET)."
else
    echo " [FAIL] Gunicorn socket file missing ($SOCKET)!"
    FAILURES=$((FAILURES + 1))
fi

# Check Nginx Service
if systemctl is-active --quiet nginx; then
    echo " [OK] Nginx service is running."
else
    echo " [FAIL] Nginx service is down!"
    FAILURES=$((FAILURES + 1))
fi

# Test Gunicorn Direct HTTP Response via Socket
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --unix-socket "$SOCKET" "http://localhost/" || echo "000")
if [[ "$HTTP_STATUS" =~ ^(200|301|302)$ ]]; then
    echo " [OK] Gunicorn responded with HTTP ${HTTP_STATUS}."
else
    echo " [FAIL] Gunicorn response test failed (HTTP ${HTTP_STATUS})!"
    FAILURES=$((FAILURES + 1))
fi

# Summary
if [[ $FAILURES -eq 0 ]]; then
    echo "===> All health checks PASSED! System is fully operational."
    exit 0
else
    echo "===> Health check encountered ${FAILURES} failure(s)!"
    exit 1
fi
