web: python manage.py collectstatic --noinput && python manage.py migrate && gunicorn vmmc_erp.wsgi --bind 0.0.0.0:$PORT --log-file -
