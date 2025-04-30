# app/dao/employee_dao.py

import uuid
from ..utils.db import get_db, close_db

def create_employee(
    empl_surname, empl_name, empl_patronymic,
    empl_role, salary, date_of_birth, date_of_start,
    phone_number, city, street, zip_code
):
    """
    Вставляє нового працівника в таблицю Employee,
    повертає згенерований id_employee.
    """
    new_emp_id = uuid.uuid4().hex[:10]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Employee (
            id_employee, empl_surname, empl_name, empl_patronymic,
            empl_role, salary, date_of_birth, date_of_start,
            phone_number, city, street, zip_code
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s
        )
    """, (
        new_emp_id,
        empl_surname, empl_name, empl_patronymic,
        empl_role, salary, date_of_birth, date_of_start,
        phone_number, city, street, zip_code
    ))
    conn.commit()
    close_db(conn)
    return new_emp_id

def get_all_employees():
    """
    Повертає список усіх працівників у вигляді списку словників:
    {id: ..., surname: ..., name: ..., role: ...}
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id_employee, empl_surname, empl_name, empl_role
        FROM Employee
        ORDER BY empl_surname, empl_name
    """)
    rows = cur.fetchall()
    close_db(conn)
    return [
        {
            'id':    r[0],
            'surname': r[1],
            'name':    r[2],
            'role':    r[3]
        }
        for r in rows
    ]

def delete_employee_by_id(emp_id):
    """
    Видаляє працівника за id_employee.
    Повертає True, якщо запис було видалено.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM Employee WHERE id_employee = %s", (emp_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    close_db(conn)
    return deleted
