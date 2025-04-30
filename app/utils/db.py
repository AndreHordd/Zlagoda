import psycopg
from flask import current_app, g

def get_db():
    """
    Повертає одне з'єднання із пулу (чи нове), збережене в g.
    """
    if 'db_conn' not in g:
        g.db_conn = psycopg.connect(current_app.config['DB_URL'])
    return g.db_conn

def close_db(error=None):
    """
    Закриває з'єднання, якщо було відкрите.
    Викликається автоматично після кожного контексту запиту.
    """
    conn = g.pop('db_conn', None)
    if conn:
        conn.close()
