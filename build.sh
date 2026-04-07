#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
# Apply migrations first to ensure the table exists
python manage.py migrate

# Create the superuser using environment variables
# The '|| true' ensures the build doesn't fail if the user already exists
python manage.py createsuperuser --noinput || true