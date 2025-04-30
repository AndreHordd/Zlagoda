import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key')
    # рядок підключення до PostgreSQL
    DB_URL = os.environ.get(
        'DATABASE_URL',
        'dbname=zlagoda user=postgres password=vladhulko2006'
    )
