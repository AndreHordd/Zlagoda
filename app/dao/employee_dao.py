"""
DAO-рівень для таблиці Employee:
створення, читання (з фільтрами та сортуванням), оновлення й видалення.
"""

import uuid
from typing import List, Dict, Any
from datetime import date

from app.utils.db import get_db, close_db


def _to_date_string(value):
    """Конвертує date або string у string (для SQLite сумісності)"""
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


# ───────────────────────── допоміжне ──────────────────────────
_COLS = {
    'id':         'id_employee',
    'surname':    'empl_surname',
    'name':       'empl_name',
    'patronymic': 'empl_patronymic',
    'role':       'empl_role',
    'salary':     'salary',
    'dob':        'date_of_birth',
    'start':      'date_of_start',
    'phone':      'phone_number',
    'city':       'city',
    'street':     'street',
    'zip':        'zip_code'
}


# ────────────────────────── CREATE ────────────────────────────
def create_employee(empl_surname: str,
                    empl_name: str,
                    empl_patronymic: str | None,
                    empl_role: str,
                    salary: float,
                    date_of_birth: str,
                    date_of_start: str,
                    phone_number: str,
                    city: str,
                    street: str,
                    zip_code: str) -> str:
    """
    Створює працівника та повертає згенерований id_employee.
    """
    new_emp_id = uuid.uuid4().hex[:10]

    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        """
        INSERT INTO Employee (
            id_employee, empl_surname, empl_name, empl_patronymic,
            empl_role, salary, date_of_birth, date_of_start,
            phone_number, city, street, zip_code
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (new_emp_id, empl_surname, empl_name, empl_patronymic,
         empl_role, salary, date_of_birth, date_of_start,
         phone_number, city, street, zip_code)
    )
    conn.commit()
    close_db(conn)

    return new_emp_id


# ─────────────────────────── READ ─────────────────────────────
def get_all_employees(sort_by: str = 'surname',
                      order: str   = 'asc',
                      role: str | None           = None,
                      surname_search: str | None = None) -> List[Dict[str, Any]]:
    """
    Повертає список усіх (або відфільтрованих) працівників.

    * sort_by — ключ із _COLS
    * order   — asc / desc
    * role    — 'manager' | 'cashier' | None
    * surname_search — підрядок для ILIKE по прізвищу
    """
    sort_col   = _COLS.get(sort_by, _COLS['surname'])
    sort_order = 'ASC' if order.lower() == 'asc' else 'DESC'

    sql    = [
        "SELECT id_employee, empl_surname, empl_name, empl_patronymic,",
        "       empl_role,  salary, date_of_birth, date_of_start,",
        "       phone_number, city, street, zip_code",
        "  FROM Employee"
    ]
    params = []
    where  = []

    if role in ('manager', 'cashier'):
        where.append("empl_role = %s")
        params.append(role)

    if surname_search:
        where.append("empl_surname ILIKE %s")
        params.append(f"%{surname_search}%")

    if where:
        sql.append(" WHERE " + " AND ".join(where))

    sql.append(f" ORDER BY {sort_col} {sort_order}")

    conn = get_db()
    cur  = conn.cursor()
    cur.execute("\n".join(sql), params)
    rows = cur.fetchall()
    close_db(conn)

    return [
        {
            "id":             r[0],
            "surname":        r[1],
            "name":           r[2],
            "patronymic":     r[3],
            "role":           r[4],
            "salary":         float(r[5]),
            "date_of_birth":  _to_date_string(r[6]),
            "date_of_start":  _to_date_string(r[7]),
            "phone_number":   r[8],
            "city":           r[9],
            "street":         r[10],
            "zip_code":       r[11]
        }
        for r in rows
    ]


def get_employee_by_id(emp_id: str) -> Dict[str, Any] | None:
    """Повертає деталі працівника або None."""
    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        """
        SELECT id_employee, empl_surname, empl_name, empl_patronymic,
               empl_role, salary, date_of_birth, date_of_start,
               phone_number, city, street, zip_code
          FROM Employee
         WHERE id_employee = %s
        """,
        (emp_id,)
    )
    r = cur.fetchone()
    close_db(conn)

    if not r:
        return None
    return {
        "id":             r[0],
        "surname":        r[1],
        "name":           r[2],
        "patronymic":     r[3],
        "role":           r[4],
        "salary":         float(r[5]),
        "date_of_birth":  _to_date_string(r[6]),
        "date_of_start":  _to_date_string(r[7]),
        "phone_number":   r[8],
        "city":           r[9],
        "street":         r[10],
        "zip_code":       r[11]
    }


# ────────────────────────── UPDATE ────────────────────────────
def update_employee(emp_id: str,
                    surname: str,
                    name: str,
                    patronymic: str | None,
                    role: str,
                    salary: float,
                    dob: str,
                    start_date: str,
                    phone: str,
                    city: str,
                    street: str,
                    zip_code: str) -> bool:
    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        """
        UPDATE Employee
           SET empl_surname   = %s,
               empl_name      = %s,
               empl_patronymic= %s,
               empl_role      = %s,
               salary         = %s,
               date_of_birth  = %s,
               date_of_start  = %s,
               phone_number   = %s,
               city           = %s,
               street         = %s,
               zip_code       = %s
         WHERE id_employee    = %s
        """,
        (surname, name, patronymic, role, salary,
         dob, start_date, phone, city, street, zip_code, emp_id)
    )
    conn.commit()
    updated = cur.rowcount > 0
    close_db(conn)
    return updated


# ────────────────────────── DELETE ────────────────────────────
def delete_employee_by_id(emp_id: str) -> bool:
    """
    Видаляє працівника та будь-який обліковий запис, прив’язаний до нього.
    """
    conn = get_db()
    cur  = conn.cursor()

    # спершу auth_user
    cur.execute("DELETE FROM auth_user WHERE employee_id = %s", (emp_id,))
    # тепер сам працівник
    cur.execute("DELETE FROM Employee WHERE id_employee = %s", (emp_id,))
    affected = cur.rowcount

    conn.commit()
    close_db(conn)
    return affected > 0
