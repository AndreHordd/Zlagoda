from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash
)
from app.utils.auth            import ensure_role
from app.dao.customer_card_dao import (
    get_all_customers, create_card, update_card,
    delete_card, generate_card_number        # ← нове
)

cashier_cards_bp = Blueprint(
    'cashier_cards', __name__, url_prefix='/customers'
)


@cashier_cards_bp.before_request
def _restrict():
    rv = ensure_role('cashier')
    if rv:
        return rv


# ───────────────────────── список ─────────────────────────────
@cashier_cards_bp.route('/')
def list_customers():
    sort_by = request.args.get('sort_by', 'surname')
    order   = request.args.get('order', 'asc')
    search  = request.args.get('search', '').strip() or None
    customers = get_all_customers(sort_by, order, search)
    return render_template('cashier/customers.html',
                           customers=customers,
                           sort_by=sort_by, order=order, search=search)


# ─────────────────────── створення ───────────────────────────
@cashier_cards_bp.route('/new', methods=('GET', 'POST'))
def new_customer():
    if request.method == 'POST':
        try:
            new_num = generate_card_number()          # ← генеруємо
            create_card(
                new_num,
                request.form['surname'], request.form['name'],
                request.form.get('patronymic') or None,
                request.form['phone'],
                request.form.get('city')   or None,
                request.form.get('street') or None,
                request.form.get('zip_code') or None,
                int(request.form['percent'])
            )
            flash(f'Картку створено (№ {new_num}).', 'success')
            return redirect(url_for('.list_customers'))
        except Exception as e:
            flash(f'Помилка: {e}', 'error')

    return render_template('cashier/customer_form.html',
                           mode='new', customer={})


# ────────────────────── редагування ───────────────────────────
@cashier_cards_bp.route('/edit/<card_number>', methods=('GET', 'POST'))
def edit_customer(card_number):
    cust = next(
        (c for c in get_all_customers() if c['card_number'] == card_number),
        None
    )
    if not cust:
        flash('Картку не знайдено.', 'error')
        return redirect(url_for('.list_customers'))

    if request.method == 'POST':
        try:
            update_card(
                card_number,
                request.form['surname'], request.form['name'],
                request.form.get('patronymic') or None,
                request.form['phone'],
                request.form.get('city')   or None,
                request.form.get('street') or None,
                request.form.get('zip_code') or None,
                int(request.form['percent'])
            )
            flash('Дані клієнта оновлено.', 'success')
            return redirect(url_for('.list_customers'))
        except Exception as e:
            flash(f'Помилка: {e}', 'error')

    return render_template('cashier/customer_form.html',
                           mode='edit', customer=cust)


# ─────────────────────── видалення ────────────────────────────
@cashier_cards_bp.route('/delete/<card_number>', methods=('POST',))
def delete_customer(card_number):
    if delete_card(card_number):
        flash('Картку клієнта видалено.', 'success')
    else:
        flash('Не вдалося видалити картку.', 'error')
    return redirect(url_for('.list_customers'))
