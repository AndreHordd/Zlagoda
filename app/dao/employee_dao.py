import uuid
from app.utils.db import get_db, close_db

def create_employee(
    empl_surname, empl_name, empl_patronymic,
    empl_role, salary, date_of_birth, date_of_start,
    phone_number, city, street, zip_code
):
    """
    Вставляє нового працівника, повертає згенерований id_employee.
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
