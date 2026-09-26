web: python manage.py migrate --noinput && gunicorn configuracao.wsgi:application --log-level info --access-logfile - --error-logfile - --bind 0.0.0.0:$PORT
