import sqlite3
import os
import re
from flask import current_app, g


class SQLiteConnectionWrapper:
    """Обгортка для sqlite3.Connection, яка конвертує PostgreSQL SQL у SQLite"""
    
    def __init__(self, conn):
        self._conn = conn
    
    def cursor(self):
        return SQLiteCursorWrapper(self._conn.cursor())
    
    def commit(self):
        return self._conn.commit()
    
    def rollback(self):
        return self._conn.rollback()
    
    def close(self):
        return self._conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        self.close()


class SQLiteCursorWrapper:
    """Обгортка для sqlite3.Cursor, яка конвертує PostgreSQL синтаксис у SQLite"""
    
    def __init__(self, cursor):
        self._cursor = cursor
    
    def execute(self, sql, params=None):
        # Конвертуємо %s плейсхолдери в ?
        if isinstance(sql, str):
            sql = sql.replace('%s', '?')
            # Конвертуємо ILIKE в LIKE (SQLite не підтримує ILIKE)
            sql = re.sub(r'\bILIKE\b', 'LIKE', sql, flags=re.IGNORECASE)
            # Видаляємо COALESCE MAX конструкції, які не працюють в деяких місцях
            # SQLite підтримує COALESCE, тому залишаємо як є
        
        if params is None:
            return self._cursor.execute(sql)
        return self._cursor.execute(sql, params)
    
    def executemany(self, sql, params):
        sql = sql.replace('%s', '?')
        return self._cursor.executemany(sql, params)
    
    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        # Конвертуємо sqlite3.Row у tuple для сумісності
        if isinstance(row, sqlite3.Row):
            return tuple(row)
        return row
    
    def fetchall(self):
        rows = self._cursor.fetchall()
        # Конвертуємо sqlite3.Row у tuple
        if rows and isinstance(rows[0], sqlite3.Row):
            return [tuple(row) for row in rows]
        return rows
    
    def close(self):
        return self._cursor.close()
    
    @property
    def rowcount(self):
        return self._cursor.rowcount


def get_db():
    """
    Повертає з'єднання з SQLite базою даних.
    """
    if 'db_conn' not in g:
        try:
            # Шлях до SQLite бази
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'zlagoda.db')
            
            # Якщо БД не існує, створюємо її
            if not os.path.exists(db_path):
                print(f"[INFO] Database not found, creating new one at {db_path}")
                from app.init_db import init_database
                init_database()
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # Для доступу до колонок за іменем
            g.db_conn = SQLiteConnectionWrapper(conn)
            
        except Exception as e:
            print(f"[WARNING] Failed to connect to database: {e}")
            g.db_conn = None
    
    return g.db_conn

def close_db(conn=None):
    """
    Закриває з'єднання, якщо було відкрите.
    Викликається автоматично після кожного контексту запиту.
    
    Якщо conn передано явно - ігноруємо (для сумісності зі старим кодом),
    оскільки з'єднання закриється автоматично через teardown.
    """
    if conn is not None:
        # Якщо передано conn - не закриваємо, це викликано всередині запиту
        return
    
    # Закриваємо тільки коли викликано без параметрів (з teardown)
    conn = g.pop('db_conn', None)
    if conn:
        try:
            conn.close()
        except Exception:
            pass

def db_available():
    """
    Перевіряє, чи доступна база даних.
    """
    conn = get_db()
    return conn is not None
