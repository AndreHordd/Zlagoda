from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, abort
)
import sqlite3
from app.dao.customer_card_dao import (
    get_all_customers_m,
    get_all_categories  # непотрібно – лишив для прикладу
)
from app.dao.customer_card_dao import (
    generate_card_number,
    create_card,
    get_all_customers_m,  # для списку
    get_all_customers_m as list_customers,  # дублюємо імпорт
    # CRUD для карток
    get_all_customers_m,
)
from app.dao.customer_card_dao import (
    get_all_customers_m as _list,  # alias
)
from app.dao.customer_card_dao import (
    get_all_customers_m,
    # CRUD-функції:
    create_card,
    update_card,
    delete_card,
    get_all_customers_m,
    get_all_customers_m
)
from app.dao.customer_card_dao import (
    get_all_customers_m,
)

# Однак потрібні саме:
from app.dao.customer_card_dao import (
    generate_card_number,
    create_card,
    get_all_customers_m,
    get_all_customers_m,
    update_card,
    delete_card
)

manager_bp = Blueprint('manager', __name__, url_prefix='/manager')

@manager_bp.route('/customers')
def customers():
    sort_by        = request.args.get('sort_by','surname')
    order          = request.args.get('order','asc')
    discount       = request.args.get('discount')
    if discount not in ('1','0'):
        discount = None
    search         = request.args.get('search','').strip() or None

    clients = get_all_customers_m(
        sort_by=sort_by,
        order=order,
        has_discount=discount,
        search=search
    )
    return render_template(
        'manager/customers.html',
        customers=clients,
        sort_by=sort_by,
        order=order,
        discount_filter=discount,
        search_filter=search
    )

@manager_bp.route('/customers/new', methods=('GET','POST'))
def new_customer():
    if request.method=='POST':
        # згенерувати новий card_number
        card_num    = generate_card_number()
        surname     = request.form['surname'].strip()
        name        = request.form['name'].strip()
        patronymic  = request.form.get('patronymic') or None
        phone       = request.form['phone'].strip()
        city        = request.form.get('city') or None
        street      = request.form.get('street') or None
        zip_code    = request.form.get('zip_code') or None
        try:
            percent = int(request.form['percent'])
            if not (0 <= percent <= 100):
                raise ValueError
        except:
            flash('Невірний формат знижки (0–100).', 'danger')
            return render_template('manager/customer_form.html',
                                   mode='new', customer={}, errors=True)

        try:
            create_card(card_num,
                        surname, name, patronymic,
                        phone, city, street, zip_code,
                        percent)
            flash(f'Клієнт створений (№ картки: {card_num}).', 'success')
            return redirect(url_for('manager.customers'))
        except Exception as e:
            flash(f'Помилка БД: {e}', 'danger')

    return render_template('manager/customer_form.html',
                           mode='new', customer={})

@manager_bp.route('/customers/edit/<card_number>', methods=('GET','POST'))
def edit_customer(card_number):
    # отримати дані картки
    from app.dao.customer_card_dao import get_all_customers_m
    cust = next((c for c in get_all_customers_m() if c['card_number']==card_number), None)
    if not cust:
        flash('Клієнта не знайдено.', 'danger')
        return redirect(url_for('manager.customers'))

    if request.method=='POST':
        surname     = request.form['surname'].strip()
        name        = request.form['name'].strip()
        patronymic  = request.form.get('patronymic') or None
        phone       = request.form['phone'].strip()
        city        = request.form.get('city') or None
        street      = request.form.get('street') or None
        zip_code    = request.form.get('zip_code') or None
        try:
            percent = int(request.form['percent'])
            if not (0 <= percent <= 100):
                raise ValueError
        except:
            flash('Невірний формат знижки (0–100).', 'danger')
            return render_template('manager/customer_form.html',
                                   mode='edit', customer=cust)

        try:
            ok = update_card(card_number,
                             surname, name, patronymic,
                             phone, city, street, zip_code,
                             percent)
            if ok:
                flash('Дані клієнта оновлено.', 'success')
            else:
                flash('Не вдалося оновити.', 'warning')
            return redirect(url_for('manager.customers'))
        except Exception as e:
            flash(f'Помилка БД: {e}', 'danger')

    return render_template('manager/customer_form.html',
                           mode='edit', customer=cust)

@manager_bp.route('/customers/delete/<card_number>', methods=('POST',))
def delete_customer(card_number):
    try:
        deleted = delete_card(card_number)
        if deleted:
            flash('Клієнта видалено.', 'success')
        else:
            flash('Не вдалося видалити клієнта.', 'danger')
    except sqlite3.IntegrityError:
        flash('Неможливо видалити — на клієнта є чек.', 'danger')
    except Exception as e:
        flash(f'Помилка БД: {e}', 'danger')
    return redirect(url_for('manager.customers'))
