from flask import (
    Blueprint, render_template,
    request, redirect, url_for,
    flash, session
)
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg.errors as db_errors

from app.dao.employee_dao import create_employee
from app.dao.auth_dao     import get_user_by_username, create_user

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=('GET','POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)

        if not user or not check_password_hash(user[1], password):
            flash('Невірний логін або пароль', 'error')
        else:
            session.clear()
            session['user_id']     = user[0]
            session['user_role']   = user[2]
            session['employee_id'] = user[3]
            session['username']    = username
            return redirect(url_for('index'))
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Ви вийшли з системи', 'success')
    return redirect(url_for('index'))

@auth_bp.route('/register', methods=('GET','POST'))
def register():
    form_data = request.form.to_dict() if request.method=='POST' else {}
    if request.method == 'POST':
        # Перевірка наявності логіна
        if get_user_by_username(form_data.get('username','')):
            flash('Логін уже зайнято', 'error')
            return render_template('auth/register.html', form_data=form_data)

        # Перетворюємо зарплату
        try:
            salary_val = float(form_data.get('salary','0'))
        except ValueError:
            flash('Зарплата має бути числом', 'error')
            return render_template('auth/register.html', form_data=form_data)

        # Створюємо працівника
        try:
            new_emp_id = create_employee(
                form_data.get('empl_surname',''),
                form_data.get('empl_name',''),
                form_data.get('empl_patronymic') or None,
                form_data.get('role',''),
                salary_val,
                form_data.get('date_of_birth',''),
                form_data.get('date_of_start',''),
                form_data.get('phone_number',''),
                form_data.get('city',''),
                form_data.get('street',''),
                form_data.get('zip_code','')
            )
        except db_errors.CheckViolation:
            flash('Некоректні дані працівника', 'error')
            return render_template('auth/register.html', form_data=form_data)
        except Exception:
            flash('Не вдалося створити працівника', 'error')
            return render_template('auth/register.html', form_data=form_data)

        # Створюємо обліковий запис
        try:
            pw_hash = generate_password_hash(form_data.get('password',''))
            create_user(
                form_data.get('username',''),
                pw_hash,
                form_data.get('role',''),
                new_emp_id
            )
        except db_errors.UniqueViolation:
            flash('Логін уже існує', 'error')
            return render_template('auth/register.html', form_data=form_data)
        except Exception:
            flash('Не вдалося створити обліковий запис', 'error')
            return render_template('auth/register.html', form_data=form_data)

        flash('Реєстрація успішна, увійдіть будь-ласка', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form_data=form_data)
