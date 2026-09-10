release: python manage.py migrate
web: gunicorn vmmc_erp.wsgi --bind 0.0.0.0:$PORT --log-file -
