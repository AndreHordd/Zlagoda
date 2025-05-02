import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key')
    # рядок підключення до PostgreSQL
    DB_URL = os.environ.get(
        'DATABASE_URL',
        'dbname=zlagoda user=postgres password=vladhulko2006'
    )

    SCHEDULER_API_ENABLED = True

    SCHEDULER_JOBS = [
        {
            'id':       'auto_promotion_job',
            'func':     'app.services.auto_promotions:run_promotion',
            'trigger':  'cron',
            'hour':     0,      # запуск щодня о 00:00
            'minute':   0
        },
    ]