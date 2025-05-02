"""
DAO-рівень для таблиці Category.
"""

from typing import List, Dict, Any
from app.utils.db import get_db, close_db


# ─────────────────────────── CREATE ────────────────────────────
def create_category(name: str) -> int:
    """
    Створює нову категорію й повертає її category_number.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(category_number), 0) + 1 FROM Category")
    new_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO Category (category_number, category_name) VALUES (%s, %s)",
        (new_id, name)
    )
    conn.commit()
    close_db(conn)
    return new_id


# ─────────────────────────── READ ──────────────────────────────
def get_all_categories(sort_by: str = 'name',
                       order: str   = 'asc') -> List[Dict[str, Any]]:
    """
    Повертає список категорій з опціональним сортуванням.

    sort_by ∈ {'id','name'}
    """
    cols = {
        'id':   'category_number',
        'name': 'category_name'
    }
    sort_col   = cols.get(sort_by, cols['name'])
    sort_order = 'ASC' if order.lower() == 'asc' else 'DESC'

    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        f"""
        SELECT category_number, category_name
          FROM Category
         ORDER BY {sort_col} {sort_order}
        """
    )
    rows = cur.fetchall()
    close_db(conn)
    return [{'id': r[0], 'name': r[1]} for r in rows]


def get_category(cat_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT category_number, category_name FROM Category WHERE category_number=%s",
        (cat_id,)
    )
    row = cur.fetchone()
    close_db(conn)
    return row


# ─────────────────────────── UPDATE ────────────────────────────
def update_category(cat_id: int, name: str) -> bool:
    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE Category SET category_name=%s WHERE category_number=%s",
        (name, cat_id)
    )
    conn.commit()
    updated = cur.rowcount > 0
    close_db(conn)
    return updated


# ─────────────────────────── DELETE ────────────────────────────
def delete_category(cat_id: int) -> bool:
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("DELETE FROM Category WHERE category_number=%s", (cat_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    close_db(conn)
    return deleted
