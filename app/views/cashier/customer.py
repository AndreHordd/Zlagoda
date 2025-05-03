# app/views/cashier/customer.py

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash
)
from app.utils.auth import ensure_role
from app.dao.customer_card_dao import (
    get_all_customers,
    create_card,
    update_card,
    delete_card,
    generate_card_number
)

cashier_cards_bp = Blueprint(
    'cashier_cards', __name__, url_prefix='/customers'
)


@cashier_cards_bp.before_request
def _restrict():
    # Забезпечуємо, що користувач має роль 'cashier'
    return ensure_role('cashier')


# ───────────────────────── список ─────────────────────────────
@cashier_cards_bp.route('/')
def list_customers():
    sort_by   = request.args.get('sort_by', 'surname')
    order     = request.args.get('order',   'asc')
    search    = request.args.get('search', '').strip() or None

    customers = get_all_customers(sort_by=sort_by,
                                  order=order,
                                  search=search)
    return render_template(
        'cashier/customers.html',
        customers=customers,
        sort_by=sort_by,
        order=order,
        search=search
    )


# ─────────────────────── створення ───────────────────────────
@cashier_cards_bp.route('/new', methods=('GET', 'POST'))
def new_customer():
    if request.method == 'POST':
        # обов'язкові поля
        surname    = request.form.get('surname', '').strip()
        name       = request.form.get('name', '').strip()
        phone      = request.form.get('phone', '').strip()
        percent_str = request.form.get('percent', '').strip()

        # додаткові (необов'язкові)
        patronymic = request.form.get('patronymic') or None
        city       = request.form.get('city') or None
        street     = request.form.get('street') or None
        zip_code   = request.form.get('zip_code') or None

        # валідація обов'язкових полів
        if not surname or not name or not phone or not percent_str:
            flash('Будь ласка, заповніть всі обов’язкові поля (прізвище, ім’я, телефон, знижка).', 'danger')
        else:
            try:
                percent = int(percent_str)
                if percent < 0 or percent > 100:
                    raise ValueError('Знижка має бути числом від 0 до 100.')
                # генеруємо унікальний номер картки
                card_number = generate_card_number()
                create_card(
                    card_number,
                    surname, name, patronymic,
                    phone, city, street, zip_code,
                    percent
                )
                flash(f'Картку створено (№ {card_number}).', 'success')
                return redirect(url_for('.list_customers'))
            except ValueError as ve:
                flash(f'Невірний формат знижки: {ve}', 'danger')
            except Exception as e:
                flash(f'Помилка при створенні картки: {e}', 'danger')

    # GET або невдала POST — показуємо форму
    return render_template(
        'cashier/customer_form.html',
        mode='new',
        customer={}
    )


# ────────────────────── редагування ───────────────────────────
@cashier_cards_bp.route('/edit/<card_number>', methods=('GET', 'POST'))
def edit_customer(card_number):
    # знаходимо існуючу картку
    cust = next(
        (c for c in get_all_customers() if c['card_number'] == card_number),
        None
    )
    if not cust:
        flash('Картку не знайдено.', 'danger')
        return redirect(url_for('.list_customers'))

    if request.method == 'POST':
        # обов'язкові поля
        surname    = request.form.get('surname', '').strip()
        name       = request.form.get('name', '').strip()
        phone      = request.form.get('phone', '').strip()
        percent_str = request.form.get('percent', '').strip()

        # додаткові (необов'язкові)
        patronymic = request.form.get('patronymic') or None
        city       = request.form.get('city') or None
        street     = request.form.get('street') or None
        zip_code   = request.form.get('zip_code') or None

        # валідація
        if not surname or not name or not phone or not percent_str:
            flash('Будь ласка, заповніть всі обов’язкові поля (прізвище, ім’я, телефон, знижка).', 'danger')
        else:
            try:
                percent = int(percent_str)
                if percent < 0 or percent > 100:
                    raise ValueError('Знижка має бути числом від 0 до 100.')
                update_card(
                    card_number,
                    surname, name, patronymic,
                    phone, city, street, zip_code,
                    percent
                )
                flash('Дані клієнта оновлено.', 'success')
                return redirect(url_for('.list_customers'))
            except ValueError as ve:
                flash(f'Невірний формат знижки: {ve}', 'danger')
            except Exception as e:
                flash(f'Помилка при оновленні картки: {e}', 'danger')

    return render_template(
        'cashier/customer_form.html',
        mode='edit',
        customer=cust
    )


# ─────────────────────── видалення ────────────────────────────
@cashier_cards_bp.route('/delete/<card_number>', methods=('POST',))
def delete_customer(card_number):
    if delete_card(card_number):
        flash('Картку клієнта видалено.', 'success')
    else:
        flash('Не вдалося видалити картку.', 'danger')
    return redirect(url_for('.list_customers'))
