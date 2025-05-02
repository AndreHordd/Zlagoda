"""
Маршрути для ролі 'cashier'.
"""

from datetime   import date, datetime
from flask      import (
    Blueprint, render_template, session,
    redirect, url_for, flash, request
)

from app.utils.auth             import ensure_role
from app.dao.product_dao        import (
    get_all_products, get_all_product_types
)
from app.dao.category_dao       import get_all_categories
from app.dao.check_dao          import (
    get_checks_by_employee, get_checks_by_employee_period
)
from app.dao.employee_dao       import get_employee_by_id

cashier_bp = Blueprint('cashier', __name__, url_prefix='/cashier')

# підблюпрінти
from .customer import cashier_cards_bp           # noqa: E402
cashier_bp.register_blueprint(cashier_cards_bp)
from . import check                              # noqa: E402


# ───────────────────────── захист ролі ──────────────────────────
@cashier_bp.before_request
def _restrict_cashier():
    rv = ensure_role('cashier')
    if rv:
        return rv


# ───────────────────────── ДАШБОРД ──────────────────────────────
@cashier_bp.route('/dashboard')
def dashboard():
    emp_id = session.get('employee_id')
    employee = get_employee_by_id(emp_id) if emp_id else None
    return render_template(
        'cashier/dashboard.html',
        employee=employee,
        username=session.get('username')
    )


# ─────────────────────  ТОВАРИ в магазині  ──────────────────────
@cashier_bp.route('/products')
def products():
    sort_by = request.args.get('sort_by', 'name')
    order   = request.args.get('order',   'asc')

    category = request.args.get('category') or None
    promo    = request.args.get('promo')            # '', '1', '0'
    search   = request.args.get('search', '').strip() or None
    field    = request.args.get('field', 'name')
    if field not in ('name', 'upc'):
        field = 'name'

    promotional = {'1': True, '0': False}.get(promo, None)

    store_products = get_all_products(sort_by, order,
                                      category, promotional,
                                      search, field)
    categories = get_all_categories()

    return render_template(
        'cashier/products.html',
        store_products=store_products,
        sort_by=sort_by, order=order,
        category=category, promo=promo,
        search=search, field=field,
        categories=categories
    )


# ─────────────────────  ТИПИ ТОВАРІВ  ───────────────────────────
@cashier_bp.route('/product_types')
def product_types():
    sort_by  = request.args.get('sort_by', 'name')
    order    = request.args.get('order', 'asc')
    category = request.args.get('category') or None
    search   = request.args.get('search', '').strip() or None

    types       = get_all_product_types(sort_by, order, category, search)
    categories  = get_all_categories()

    return render_template(
        'cashier/product_types.html',
        product_types=types,
        sort_by=sort_by, order=order,
        category=category, search=search,
        categories=categories
    )


# ─────────────────────  МОЇ ЧЕКИ  ───────────────────────────────
@cashier_bp.route('/my_receipts')
def my_receipts():
    employee_id = session.get('employee_id')
    if not employee_id:
        flash('Неможливо отримати чеки: невідомий касир', 'error')
        return redirect(url_for('auth.login'))

    today_flag = request.args.get('today')
    date_from  = request.args.get('from') or None
    date_to    = request.args.get('to')   or None
    sort_by    = request.args.get('sort_by', 'date')
    order      = request.args.get('order',   'desc')

    if today_flag == '1':
        date_from = date_to = date.today().isoformat()

    try:
        df = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
    except ValueError:
        df = None
    try:
        dt = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None
    except ValueError:
        dt = None

    if df or dt:
        receipts = get_checks_by_employee_period(
            employee_id, df, dt, sort_by, order
        )
    else:
        receipts = get_checks_by_employee(employee_id, sort_by, order)

    return render_template(
        'cashier/my_receipts.html',
        receipts=receipts,
        date_from=date_from, date_to=date_to,
        sort_by=sort_by, order=order
    )
