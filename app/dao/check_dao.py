"""
DAO-рівень для таблиць "check" та Sale.
Містить: create_check, списки чеків (із сортуванням і фільтром за датами),
деталі окремого чеку.
"""

import uuid
from datetime import datetime, date
from decimal   import Decimal, ROUND_HALF_UP
from collections import defaultdict
from typing    import List, Dict, Any

from app.utils.db import get_db, close_db


# ────────────────────────────── CREATE ──────────────────────────────
def create_check(check_number: str | None,
                 employee_id: str,
                 card_number: str | None,
                 sales: List[Dict[str, Any]]) -> str:
    """
    Створює чек разом із рядками Sale й одразу зменшує залишок у Store_Product.

    sales = [{'upc': '123456789012', 'qty': 2}, …]

    * Агрегує однакові UPC, перевіряє, що qty ≤ залишок.
    * Рахує підсумок, знижку (% поля percent у Customer_Card), VAT=20 %.
    * У sum_total записує суму ДО СПЛАТИ.
    * Повертає номер чека (згенерує, якщо None).
    * Кидає ValueError(HTML-рядок), якщо є помилки залишку чи відсутній товар.
    """
    if not check_number:
        check_number = uuid.uuid4().hex[:10]

    # ── агрегуємо однакові UPC ────────────────────────────────────────
    aggregated: dict[str, int] = defaultdict(int)
    for item in sales:
        aggregated[item['upc']] += int(item['qty'])
    sales_agg = [{'upc': u, 'qty': q} for u, q in aggregated.items()]

    conn = get_db()
    cur  = conn.cursor()

    # ── відсоток знижки за карткою клієнта ────────────────────────────
    discount_percent = Decimal('0')
    if card_number:
        cur.execute("SELECT percent FROM Customer_Card WHERE card_number=%s",
                    (card_number,))
        row = cur.fetchone()
        if row:
            discount_percent = Decimal(row[0]).quantize(Decimal('1'))

    # ── перевірка залишків + subtotal ─────────────────────────────────
    errors   = []
    subtotal = Decimal('0.00')

    for item in sales_agg:
        cur.execute(
            "SELECT selling_price, products_number "
            "FROM Store_Product WHERE UPC=%s",
            (item['upc'],)
        )
        row = cur.fetchone()
        if row is None:
            errors.append(f"Товар <strong>{item['upc']}</strong> не існує.")
            continue

        price, stock = row
        if item['qty'] > stock:
            errors.append(
                f"Для <strong>{item['upc']}</strong> доступно {stock}, "
                f"запитано {item['qty']}."
            )
        subtotal += (price * item['qty']).quantize(Decimal('0.01'))

    if errors:
        conn.rollback()
        close_db(conn)
        raise ValueError("<br>".join(errors))

    # ── підсумки (знижка, VAT, до сплати) ────────────────────────────
    discount = (subtotal * discount_percent / 100).quantize(Decimal('0.01'))
    taxable  = subtotal - discount
    vat      = (taxable * Decimal('0.20')).quantize(Decimal('0.01'))
    payable  = (taxable + vat).quantize(Decimal('0.01'), ROUND_HALF_UP)

    # ── шапка чека ────────────────────────────────────────────────────
    cur.execute(
        """
        INSERT INTO "check"
              (check_number, id_employee, card_number, print_date, sum_total)
        VALUES (%s,%s,%s,%s,%s)
        """,
        (check_number, employee_id, card_number, datetime.now(), payable)
    )

    # ── рядки Sale + оновлення залишку ────────────────────────────────
    for item in sales_agg:
        cur.execute(
            """
            INSERT INTO Sale
                  (UPC, check_number, product_number, selling_price)
            VALUES (
                %s, %s, %s,
                (SELECT selling_price FROM Store_Product WHERE UPC=%s)
            )
            """,
            (item['upc'], check_number, item['qty'], item['upc'])
        )
        cur.execute(
            "UPDATE Store_Product "
            "SET products_number = products_number - %s "
            "WHERE UPC=%s",
            (item['qty'], item['upc'])
        )

    conn.commit()
    close_db(conn)
    return check_number


# ─────────────────────── Списки чеків (із сортуванням) ──────────────────────
_VALID_COLS = {
    'number': 'check_number',
    'date':   'print_date',
    'total':  'sum_total'
}


def get_checks_by_employee(employee_id: str,
                           sort_by: str = 'date',
                           order: str   = 'desc'):
    """
    Усі чеки касира з обраним сортуванням.
    """
    return get_checks_by_employee_period(employee_id, None, None,
                                         sort_by, order)


def get_checks_by_employee_period(employee_id: str,
                                  date_from: date | None,
                                  date_to:   date | None,
                                  sort_by: str = 'date',
                                  order:   str = 'desc'):
    """
    Чеки касира у межах [date_from; date_to] (включно) + сортування.
    """
    sort_col   = _VALID_COLS.get(sort_by, _VALID_COLS['date'])
    sort_order = 'ASC' if order.lower() == 'asc' else 'DESC'

    sql = [
        'SELECT check_number, print_date, sum_total',
        'FROM "check"',
        'WHERE id_employee = %s'
    ]
    params = [employee_id]

    if date_from:
        sql.append('AND DATE(print_date) >= %s')
        params.append(date_from)
    if date_to:
        sql.append('AND DATE(print_date) <= %s')
        params.append(date_to)

    sql.append(f'ORDER BY {sort_col} {sort_order}')

    conn = get_db()
    cur  = conn.cursor()
    cur.execute(" ".join(sql), params)
    rows = cur.fetchall()
    close_db(conn)

    return [
        {
            "number": r[0],
            "date":   r[1].strftime("%Y-%m-%d %H:%M:%S"),
            "total":  float(r[2])
        } for r in rows
    ]


# ───────────────────────────── Деталі чека ─────────────────────────────
def get_check_details(check_number: str) -> Dict[str, Any] | None:
    """
    Повертає детальну інформацію по чеку:
    {
      'header': {...},
      'items' : [ {...}, ... ]
    }
    """
    conn = get_db()
    cur  = conn.cursor()

    # шапка
    cur.execute(
        """
        SELECT  c.check_number,
                c.print_date,
                c.sum_total,
                e.empl_surname || ' ' || e.empl_name AS cashier,
                cc.card_number,
                COALESCE(cc.percent,0)              AS discount_percent
        FROM "check"        AS c
        JOIN Employee       AS e  ON e.id_employee = c.id_employee
        LEFT JOIN Customer_Card AS cc USING(card_number)
        WHERE c.check_number = %s
        """,
        (check_number,)
    )
    head = cur.fetchone()
    if not head:
        close_db(conn)
        return None

    header = {
        "number":  head[0],
        "date":    head[1].strftime("%Y-%m-%d %H:%M:%S"),
        "total":   float(head[2]),
        "cashier": head[3],
        "card":    head[4],
        "disc":    int(head[5])
    }

    # позиції
    cur.execute(
        """
        SELECT s.upc,
               p.product_name,
               s.product_number,
               s.selling_price
        FROM Sale AS s
        JOIN Store_Product AS sp USING(upc)
        JOIN Product        AS p  ON p.id_product = sp.id_product
        WHERE s.check_number = %s
        """,
        (check_number,)
    )
    rows = cur.fetchall()
    close_db(conn)

    items = [
        {
            "upc":   r[0],
            "name":  r[1],
            "qty":   r[2],
            "price": float(r[3]),
            "total": float(r[3] * r[2])
        } for r in rows
    ]

    subtotal = sum(i["total"] for i in items)
    discount = subtotal * header["disc"] / 100
    taxable  = subtotal - discount
    vat      = taxable * 0.20

    header.update({
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "vat":      round(vat, 2)
    })

    return {"header": header, "items": items}
# ─────────────────────── СПИСОК УСІХ ЧЕКІВ ────────────────────────
def get_all_checks(sort_by: str = 'date',
                   order: str   = 'desc') -> list[dict]:
    """
    Повертає простий список чеків (для звіту).
    """
    cols = {
        'number': 'check_number',
        'date':   'print_date',
        'total':  'sum_total'
    }
    sort_col   = cols.get(sort_by, cols['date'])
    sort_order = 'ASC' if order.lower() == 'asc' else 'DESC'

    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        f"""
        SELECT check_number, print_date, id_employee, sum_total
          FROM "check"
         ORDER BY {sort_col} {sort_order}
        """
    )
    rows = cur.fetchall()
    close_db(conn)
    return [
        {
            'number': r[0],
            'date':   r[1].strftime('%Y-%m-%d %H:%M:%S'),
            'cashier': r[2],
            'total':  float(r[3])
        } for r in rows
    ]


# ───────────────────── ДЛЯ МЕНЕДЖЕРА ─────────────────────
def get_checks_all_period(date_from: date | None,
                          date_to:   date | None,
                          sort_by: str = 'date',
                          order:   str = 'desc') -> list[dict]:
    """
    Усі чеки (усіх касирів) за період [date_from; date_to].
    Повертає список словників:
      {'number','date','total','cashier_id','cashier_name'}
    """
    sort_col = _VALID_COLS.get(sort_by, _VALID_COLS['date'])
    sort_ord = 'ASC' if order.lower() == 'asc' else 'DESC'

    sql = [
        """SELECT c.check_number,
                  c.print_date,
                  c.sum_total,
                  e.id_employee,
                  e.empl_surname || ' ' || e.empl_name AS cashier
           FROM "check" AS c
           JOIN Employee AS e ON e.id_employee = c.id_employee"""
    ]
    params = []

    if date_from:
        sql.append("WHERE DATE(c.print_date) >= %s")
        params.append(date_from)
    if date_to:
        sql.append("AND DATE(c.print_date) <= %s" if params else
                   "WHERE DATE(c.print_date) <= %s")
        params.append(date_to)

    sql.append(f"ORDER BY {sort_col} {sort_ord}")

    conn = get_db()
    cur  = conn.cursor()
    cur.execute(" ".join(sql), params)
    rows = cur.fetchall()
    close_db(conn)

    return [
        {
            "number": r[0],
            "date":   r[1].strftime("%Y-%m-%d %H:%M:%S"),
            "total":  float(r[2]),
            "cashier_id":   r[3],
            "cashier_name": r[4]
        } for r in rows
    ]


def get_checks_by_employee_period_mgr(employee_id: str,
                                      date_from: date | None,
                                      date_to:   date | None,
                                      sort_by: str = 'date',
                                      order:   str = 'desc') -> list[dict]:
    """
    Те саме, що get_checks_by_employee_period, але повертає ще й ім'я касира.
    """
    checks = get_checks_by_employee_period(employee_id,
                                           date_from,
                                           date_to,
                                           sort_by,
                                           order)
    # додаємо ПІБ касира
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""SELECT empl_surname||' '||empl_name
                     FROM Employee WHERE id_employee=%s""",
                (employee_id,))
    name = cur.fetchone()[0] if cur.rowcount else '—'
    close_db(conn)

    for chk in checks:
        chk['cashier_name'] = name
    return checks


def get_total_sales_by_cashier_period(employee_id: str,
                                     date_from: date | None,
                                     date_to:   date | None) -> Decimal:
    """
    Повертає загальну суму sum_total з таблиці "check"
    для даного касира в період [date_from; date_to].
    """
    sql = ["SELECT COALESCE(SUM(sum_total),0) FROM \"check\" WHERE id_employee = %s"]
    params = [employee_id]
    if date_from:
        sql.append("AND DATE(print_date) >= %s")
        params.append(date_from)
    if date_to:
        sql.append("AND DATE(print_date) <= %s")
        params.append(date_to)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(" ".join(sql), params)
    total = cur.fetchone()[0]  # Decimal
    close_db(conn)
    return total

def get_total_sales_all_period(date_from: date | None,
                               date_to:   date | None) -> Decimal:
    """
    Повертає загальну суму sum_total з таблиці "check"
    для всіх касирів у період [date_from; date_to].
    """
    sql = ["SELECT COALESCE(SUM(sum_total),0) FROM \"check\""]
    params = []
    where = []
    if date_from:
        where.append("DATE(print_date) >= %s")
        params.append(date_from)
    if date_to:
        where.append("DATE(print_date) <= %s")
        params.append(date_to)
    if where:
        sql.append("WHERE " + " AND ".join(where))
    conn = get_db()
    cur = conn.cursor()
    cur.execute(" ".join(sql), params)
    total = cur.fetchone()[0]
    close_db(conn)
    return total

def get_quantity_sold_period(upc: str,
                             date_from: date | None,
                             date_to:   date | None) -> int:
    """
    Повертає загальну кількість одиниць товару з Sale.UPC=upc,
    проданих у період [date_from; date_to].
    """
    sql = [
        "SELECT COALESCE(SUM(s.product_number),0)",
        "FROM Sale AS s",
        "JOIN \"check\" AS c ON s.check_number = c.check_number",
        "WHERE s.UPC = %s"
    ]
    params = [upc]
    if date_from:
        sql.append("AND DATE(c.print_date) >= %s")
        params.append(date_from)
    if date_to:
        sql.append("AND DATE(c.print_date) <= %s")
        params.append(date_to)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(" ".join(sql), params)
    qty = cur.fetchone()[0]
    close_db(conn)
    return qty

def delete_check(check_number: str) -> bool:
    """
    Видаляє чек із таблиці "Check" (іменований приводу ON DELETE CASCADE
    видалить спочатку всі рядки в Sale з цим check_number).
    Повертає True, якщо чек успішно видалено.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM "check" WHERE check_number=%s', (check_number,))
    conn.commit()
    deleted = cur.rowcount > 0
    close_db(conn)
    return deleted
