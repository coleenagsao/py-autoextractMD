# Week 2: Forms and API Exploration
# Author: Coleen Therese A. Agsao

from decouple import config

# save aws_access_key_id and aws_secret_access_key from .env
key_id = config('aws_access_key_id', default='')
access_key = config('aws_secret_access_key', default='')

print(key_id, access_key)