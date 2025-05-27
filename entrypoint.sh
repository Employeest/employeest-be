#!/bin/sh

set -e

echo "--- [Entrypoint] Running MAKEMIGRATIONS ---"
python manage.py makemigrations
echo "--- [Entrypoint] Running Django Migrations ---"
python manage.py migrate

echo "--- [Entrypoint] Creating superuser (if it does not exist) ---"
python manage.py shell <<EOF
import os
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

User = get_user_model() # Gets your AUTH_USER_MODEL
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if username and email and password:
    try:
        if User.objects.filter(username=username).exists():
            print(f'[Entrypoint] Superuser {username} already exists.')
        else:
            User.objects.create_superuser(username, email, password)
            print(f'[Entrypoint] Superuser {username} created successfully.')
    except MultipleObjectsReturned:
        print(f'[Entrypoint] Multiple users found with username {username}. Superuser creation skipped.')
    except Exception as e:
        print(f'[Entrypoint] An error occurred during superuser creation: {e}')
else:
    print('[Entrypoint] DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, or DJANGO_SUPERUSER_PASSWORD not fully set. Skipping superuser creation.')
EOF

echo "--- [Entrypoint] Starting Django Development Server ---"
exec python manage.py runserver 0.0.0.0:8000
