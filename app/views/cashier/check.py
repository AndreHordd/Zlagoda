from markupsafe import Markup
from flask import (
    render_template, request, redirect,
    url_for, flash, session
)
from app.dao.check_dao import create_check, get_check_details
from app.dao.product_dao         import get_all_products
from app.dao.customer_card_dao   import get_all_cards
from .routes                     import cashier_bp

# ───────────────────── НОВИЙ маршрут ─────────────────────
@cashier_bp.route('/receipt/<check_number>')
def receipt_detail(check_number):
    details = get_check_details(check_number)
    if not details:
        abort(404)
    return render_template('cashier/receipt_detail.html', **details)


@cashier_bp.route('/create_receipt', methods=('GET', 'POST'))
def create_receipt():
    products = get_all_products(sort_by='name', order='asc')
    cards    = get_all_cards()

    employee_id = session.get('employee_id')
    if not employee_id:
        flash('Увійдіть заново, щоб створити чек.', 'error')
        return redirect(url_for('auth.login'))

    # ── зберегти введені значення, якщо POST з помилкою ──────────────────
    form_data = request.form.to_dict() if request.method == 'POST' else {}
    indices   = sorted({k.split('_')[1] for k in form_data if k.startswith('upc_')}, key=int) or [1]

    if request.method == 'POST':
        # зібрати коректні позиції
        sales = []
        for idx in indices:
            upc = form_data.get(f'upc_{idx}', '').strip()
            try:
                qty = int(form_data.get(f'qty_{idx}', 0))
            except ValueError:
                qty = 0
            if upc and qty > 0:
                sales.append({'upc': upc, 'qty': qty})

        if not sales:
            flash('Додайте хоча б один коректний товар.', 'error')
            return render_template('cashier/create_receipt.html',
                                   products=products, cards=cards,
                                   form_data=form_data, indices=indices)

        try:
            chk_no = create_check(
                None,
                employee_id,
                form_data.get('card_number') or None,
                sales
            )
            flash(Markup(
                f'<div class="alert alert-success">'
                f'Чек <strong>{chk_no}</strong> створено успішно.'
                f'</div>'
            ), 'message')
            return redirect(url_for('cashier.my_receipts'))

        except ValueError as e:
            # показати всі зібрані помилки, при цьому введені дані залишаються
            flash(Markup(
                f'<div class="alert alert-danger">'
                f'{e}'
                f'</div>'
            ), 'message')
            return render_template('cashier/create_receipt.html',
                                   products=products, cards=cards,
                                   form_data=form_data, indices=indices)

        except Exception as e:
            flash(Markup(
                f'<div class="alert alert-danger">'
                f'Невідома помилка: {e}'
                f'</div>'
            ), 'message')
            return render_template('cashier/create_receipt.html',
                                   products=products, cards=cards,
                                   form_data=form_data, indices=indices)

    return render_template('cashier/create_receipt.html',
                           products=products, cards=cards,
                           form_data=form_data, indices=indices)
