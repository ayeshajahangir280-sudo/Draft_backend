web: python manage.py migrate --noinput && python manage.py seed_demo && python -m daphne -b 0.0.0.0 -p ${PORT:-3000} config.asgi:application
