import random

from app.utils.db import get_db, close_db

# ──────────────── допоміжне ──────────────────────────────────
def generate_card_number() -> str:
    """
    Генерує унікальний card_number формату 'C' + 12 цифр.
    Перевіряє відсутність у БД.
    """
    conn = get_db()
    cur  = conn.cursor()
    while True:
        new_num = 'C' + ''.join(random.choices('0123456789', k=12))
        cur.execute("SELECT 1 FROM Customer_Card WHERE card_number=%s",
                    (new_num,))
        if cur.fetchone() is None:
            close_db(conn)
            return new_num
    # (цикл практично завжди завершується за 1-2 ітерації)

# ──────────────── CREATE ─────────────────────────────────────
def create_card(card_number: str,
                surname: str,
                name: str,
                patronymic: str | None,
                phone: str,
                city: str | None,
                street: str | None,
                zip_code: str | None,
                percent: int) -> None:
    """
    Створює картку з указаним card_number.
    """
    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        """
        INSERT INTO Customer_Card
               (card_number, cust_surname, cust_name, cust_patronymic,
                phone_number, city, street, zip_code, percent)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (card_number, surname, name, patronymic,
         phone, city, street, zip_code, percent)
    )
    conn.commit()
    close_db(conn)
# ──────────────── READ ────────────────
def get_all_cards() -> list[dict]:
    """
    Повертає список усіх карток клієнтів у вигляді:
    [{'number', 'name', 'percent'}], відсортований за номером картки.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT card_number, cust_surname, cust_name, percent
          FROM Customer_Card
         ORDER BY card_number
    """)
    rows = cur.fetchall()
    close_db(conn)
    return [
        {'number': r[0], 'name': f"{r[1]} {r[2]}", 'percent': r[3]}
        for r in rows
    ]

# (інші методи create/update/delete залишаються без змін)


# ──────────────── UPDATE ────────────────
def update_card(card_number: str,
                surname: str,
                name: str,
                patronymic: str | None,
                phone: str,
                city: str | None,
                street: str | None,
                zip_code: str | None,
                percent: int) -> bool:
    """
    Оновлює дані існуючої картки клієнта; повертає True, якщо оновлено.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE Customer_Card
           SET cust_surname=%s,
               cust_name=%s,
               cust_patronymic=%s,
               phone_number=%s,
               city=%s,
               street=%s,
               zip_code=%s,
               percent=%s
         WHERE card_number=%s
        """,
        (surname, name, patronymic, phone,
         city, street, zip_code, percent, card_number)
    )
    conn.commit()
    updated = cur.rowcount > 0
    close_db(conn)
    return updated

# ──────────────── DELETE ────────────────
def delete_card(card_number: str) -> bool:
    """
    Видаляє картку клієнта; повертає True, якщо видалено.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM Customer_Card WHERE card_number=%s",
        (card_number,)
    )
    conn.commit()
    deleted = cur.rowcount > 0
    close_db(conn)
    return deleted

def get_all_customers_sorted():
    """
    Повертає список усіх постійних клієнтів,
    відсортованих за cust_surname.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT
          card_number,
          cust_surname,
          cust_name,
          cust_patronymic,
          phone_number,
          city,
          street,
          zip_code,
          percent
        FROM Customer_Card
        ORDER BY cust_surname
    """)
    rows = cur.fetchall()
    close_db(conn)
    return [
        {
            'card_number':       r[0],
            'surname':           r[1],
            'name':              r[2],
            'patronymic':        r[3],
            'phone':             r[4],
            'city':              r[5],
            'street':            r[6],
            'zip_code':          r[7],
            'percent':           r[8],
        }
        for r in rows
    ]

def get_all_customers(sort_by: str = 'surname', order: str = 'asc', search: str | None = None):
    """
    Повертає список усіх постійних клієнтів з деталями,
    відсортованих за довільною колонкою і напрямком.
    Опціонально — пошук за прізвищем.
    """
    cols = {
        'card_number': 'card_number',
        'surname': 'cust_surname',
        'name': 'cust_name',
        'patronymic': 'cust_patronymic',
        'phone': 'phone_number',
        'city': 'city',
        'street': 'street',
        'zip_code': 'zip_code',
        'percent': 'percent'
    }
    sort_col = cols.get(sort_by, cols['surname'])
    sort_order = 'ASC' if order.lower() == 'asc' else 'DESC'

    sql = [
        "SELECT card_number, cust_surname, cust_name, cust_patronymic,",
        "       phone_number, city, street, zip_code, percent",
        "  FROM Customer_Card"
    ]
    params = []
    where = []
    if search:
        where.append("cust_surname ILIKE %s")
        params.append(f"%{search}%")
    if where:
        sql.append("WHERE " + " AND ".join(where))
    sql.append(f"ORDER BY {sort_col} {sort_order}")

    conn = get_db()
    cur = conn.cursor()
    cur.execute(" ".join(sql), params)
    rows = cur.fetchall()
    close_db(conn)
    return [
        {
            'card_number': r[0],
            'surname':     r[1],
            'name':        r[2],
            'patronymic':  r[3],
            'phone':       r[4],
            'city':        r[5],
            'street':      r[6],
            'zip_code':    r[7],
            'percent':     r[8]
        }
        for r in rows
    ]

# ───────────────────── для менеджера ─────────────────────
def get_all_customers_m(
    sort_by: str = 'surname',
    order: str = 'asc',
    min_percent: int | None = None,
    max_percent: int | None = None,
    search: str | None = None
) -> list[dict]:
    """
    Повертає список постійних клієнтів з довільним сортуванням
    і фільтрами по мінімальній/максимальній знижці та пошуком за прізвищем.
    """
    cols = {
        'card_number': 'card_number',
        'surname':     'cust_surname',
        'name':        'cust_name',
        'patronymic':  'cust_patronymic',
        'phone':       'phone_number',
        'city':        'city',
        'street':      'street',
        'zip_code':    'zip_code',
        'percent':     'percent'
    }
    sort_col   = cols.get(sort_by, cols['surname'])
    sort_order = 'ASC' if order.lower()=='asc' else 'DESC'

    sql    = ["SELECT card_number, cust_surname, cust_name, cust_patronymic,",
              "       phone_number, city, street, zip_code, percent",
              "  FROM Customer_Card"]
    where  = []
    params = []

    if min_percent is not None:
        where.append("percent >= %s")
        params.append(min_percent)
    if max_percent is not None:
        where.append("percent <= %s")
        params.append(max_percent)
    if search:
        where.append("cust_surname ILIKE %s")
        params.append(f"%{search}%")

    if where:
        sql.append("WHERE " + " AND ".join(where))
    sql.append(f"ORDER BY {sort_col} {sort_order}")

    conn = get_db()
    cur  = conn.cursor()
    cur.execute(" ".join(sql), params)
    rows = cur.fetchall()
    close_db(conn)

    return [{
        'card_number': r[0],
        'surname':     r[1],
        'name':        r[2],
        'patronymic':  r[3],
        'phone':       r[4],
        'city':        r[5],
        'street':      r[6],
        'zip_code':    r[7],
        'percent':     r[8]
    } for r in rows]
