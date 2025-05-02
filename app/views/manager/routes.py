"""
Маршрути, доступні менеджеру (URL-префікс /manager).

• /dashboard                    – дашборд
• /employees (+new /edit /delete) – повний CRUD працівників
• /customers                    – список постійних клієнтів
• /categories (+edit /delete)   – список + CRUD категорій
• /products                     – типи товарів
• /store_products               – товари у магазині
• /reports                      – сторінка звітів
• /reports/preview/<table>      – HTML-фрагмент для попереднього перегляду
"""

from datetime import date, timedelta

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, abort
)

from app.dao.check_dao import get_check_details, get_checks_by_employee_period_mgr, get_checks_all_period, \
    get_total_sales_by_cashier_period, get_total_sales_all_period, get_quantity_sold_period
from app.utils.auth import ensure_role

# ─── DAO ────────────────────────────────────────────────────────────
from app.dao.employee_dao import (
    get_all_employees, get_employee_by_id,
    create_employee,   update_employee,
    delete_employee_by_id
)
from app.dao.customer_card_dao import get_all_customers_sorted
from app.dao.category_dao import (
    get_all_categories, create_category,
    update_category,     delete_category
)
from app.dao.product_dao import (
    get_all_product_types, get_all_products
)

from app.dao.check_dao import (
    get_checks_all_period,
    get_checks_by_employee_period_mgr,
    get_check_details
)
from app.dao.employee_dao import get_all_employees   # для списку касирів
from datetime import datetime, date

manager_bp = Blueprint('manager', __name__, url_prefix='/manager')


# ───────────────────────── Захист ролі ────────────────────────────
@manager_bp.before_request
def _restrict_manager():
    return ensure_role('manager')


# ═══════════════ 1. DASHBOARD ═══════════════
@manager_bp.route('/dashboard')
def dashboard():
    return render_template('manager/dashboard.html')


# ═══════════════ 2. ПРАЦІВНИКИ ═══════════════
@manager_bp.route('/employees')
def employees():
    sort_by = request.args.get('sort_by', 'surname')
    order   = request.args.get('order',   'asc')

    role_filter   = request.args.get('role') or None
    if role_filter not in ('manager', 'cashier'):
        role_filter = None

    search_filter = request.args.get('search', '').strip() or None

    employees = get_all_employees(sort_by, order,
                                  role_filter, search_filter)

    return render_template(
        'manager/employees.html',
        employees=employees,
        sort_by=sort_by, order=order,
        role_filter=role_filter,
        search_filter=search_filter
    )


@manager_bp.route('/employees/new', methods=('GET', 'POST'))
def new_employee():
    """
    Створення працівника з одночасним створенням auth_user
    відбувається на рівні DAO create_employee та create_user.
    На цій формі ми збираємо лише дані працівника.
    """
    if request.method == 'POST':
        try:
            create_employee(
                request.form['surname'],
                request.form['name'],
                request.form.get('patronymic') or None,
                request.form['role'],
                float(request.form['salary']),
                request.form['dob'],
                request.form['start_date'],
                request.form['phone'],
                request.form['city'],
                request.form['street'],
                request.form['zip_code']
            )
            flash('Працівника створено.', 'success')
            return redirect(url_for('manager.employees'))
        except ValueError:
            flash('Невірний формат числових полів.', 'danger')
        except Exception as e:
            flash(f'Помилка: {e}', 'danger')

    return render_template('manager/employee_form.html',
                           mode='new', employee={})


@manager_bp.route('/employees/edit/<emp_id>', methods=('GET', 'POST'))
def edit_employee(emp_id: str):
    emp = get_employee_by_id(emp_id)
    if not emp:
        flash('Працівника не знайдено.', 'danger')
        return redirect(url_for('manager.employees'))

    if request.method == 'POST':
        try:
            update_employee(
                emp_id,
                request.form['surname'],
                request.form['name'],
                request.form.get('patronymic') or None,
                request.form['role'],
                float(request.form['salary']),
                request.form['dob'],
                request.form['start_date'],
                request.form['phone'],
                request.form['city'],
                request.form['street'],
                request.form['zip_code']
            )
            flash('Дані працівника оновлено.', 'success')
            return redirect(url_for('manager.employees'))
        except ValueError:
            flash('Невірний формат числових полів.', 'danger')
        except Exception as e:
            flash(f'Помилка: {e}', 'danger')

    return render_template('manager/employee_form.html',
                           mode='edit', employee=emp)


@manager_bp.route('/employees/delete/<emp_id>', methods=('POST',))
def delete_employee(emp_id: str):
    """
    Видаляє працівника та обліковий запис, якщо був прив’язаний.
    """
    if delete_employee_by_id(emp_id):
        flash('Працівника видалено.', 'success')
    else:
        flash('Не вдалося видалити працівника.', 'danger')
    return redirect(url_for('manager.employees'))


# ═══════════════ 3. ПОСТІЙНІ КЛІЄНТИ ═══════════════
# ───── імпорт DAO (лиш один) ─────────────────────────
from app.dao.customer_card_dao import get_all_customers_m

# ═══════════════ ПОСТІЙНІ КЛІЄНТИ ═══════════════
@manager_bp.route('/customers')
def customers():
    # сортування
    sort_by = request.args.get('sort_by', 'surname')
    order   = request.args.get('order',   'asc')

    # фільтр «є знижка / без знижки»
    discount = request.args.get('discount')           # '1' | '0' | None
    if discount not in ('1', '0'):
        discount = None

    # пошук за прізвищем
    search = request.args.get('search', '').strip() or None

    # отримуємо дані
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



# ═══════════════ 4. КАТЕГОРІЇ ═══════════════
@manager_bp.route('/categories', methods=('GET', 'POST'))
def categories():
    """
    GET  – список з сортуванням;
    POST – додати нову категорію (поле new_name).
    """
    if request.method == 'POST':
        name = request.form.get('new_name', '').strip()
        if not name:
            flash('Назва не може бути порожньою.', 'warning')
        else:
            try:
                create_category(name)
                flash('Категорію додано.', 'success')
            except Exception as e:
                flash(f'Помилка: {e}', 'danger')
        return redirect(url_for('manager.categories'))

    sort_by = request.args.get('sort_by', 'name')  # id | name
    order   = request.args.get('order',   'asc')
    cats    = get_all_categories(sort_by, order)
    return render_template('manager/categories.html',
                           categories=cats,
                           sort_by=sort_by, order=order)


@manager_bp.route('/categories/edit/<int:cat_id>', methods=('GET', 'POST'))
def edit_category(cat_id: int):
    cat = next((c for c in get_all_categories() if c['id'] == cat_id), None)
    if not cat:
        flash('Категорію не знайдено.', 'danger')
        return redirect(url_for('manager.categories'))

    if request.method == 'POST':
        new_name = request.form['name_category'].strip()
        if not new_name:
            flash('Назва не може бути порожньою.', 'warning')
        else:
            try:
                update_category(cat_id, new_name)
                flash('Категорію оновлено.', 'success')
                return redirect(url_for('manager.categories'))
            except Exception as e:
                flash(f'Помилка: {e}', 'danger')

    return render_template('manager/categories_form.html',
                           mode='edit', category=cat)


@manager_bp.route('/categories/delete/<int:cat_id>', methods=('POST',))
def delete_category_route(cat_id: int):
    if delete_category(cat_id):
        flash('Категорію видалено.', 'success')
    else:
        flash('Не вдалося видалити категорію.', 'danger')
    return redirect(url_for('manager.categories'))


# ═══════════════ 5. ТИПИ ТОВАРІВ ═══════════════
@manager_bp.route('/products')
def products():
    sort_by  = request.args.get('sort_by', 'name')
    order    = request.args.get('order',   'asc')
    category = request.args.get('category') or None
    search   = request.args.get('search', '').strip() or None

    types = get_all_product_types(sort_by, order, category, search)
    cats  = get_all_categories()
    return render_template('manager/product_types.html',
                           product_types=types,
                           categories=cats,
                           sort_by=sort_by, order=order,
                           category=category, search=search)


# ═══════════════ 6. ТОВАРИ У МАГАЗИНІ ═══════════════
@manager_bp.route('/store_products')
def store_products():
    # сортування
    sort_by = request.args.get('sort_by', 'quantity')
    order   = request.args.get('order',   'desc')

    # фільтри
    category = request.args.get('category') or None          # select
    promo    = request.args.get('promo')                     # '', '1', '0'
    promotional = {'1': True, '0': False}.get(promo, None)   # → True / False / None

    # пошук
    field  = request.args.get('field', 'name')
    if field not in ('name', 'upc', 'category', 'characteristics'):
        field = 'name'
    search = request.args.get('search', '').strip() or None

    # DAO
    items = get_all_products(sort_by, order,
                             category,
                             promotional,
                             search,
                             field)
    cats  = get_all_categories()

    return render_template(
        'manager/store_products.html',
        store_products=items,
        categories=cats,
        sort_by=sort_by, order=order,
        category=category,
        promo=promo,                   # ← передаємо сировий рядок '' | '1' | '0'
        field=field,
        search=search
    )
# ═══════════════ 7. PREVIEW для звітів ═══════════════
@manager_bp.route('/reports/preview/<table>')
def reports_preview(table: str):
    """
    Повертає HTML-фрагмент таблиці для модального попереднього перегляду.
    Доступні значення <table>:
        employees, customers, categories,
        product_types, store_products
    """
    data_map = {
        'employees':      lambda: get_all_employees('surname', 'asc'),
        'customers':      get_all_customers_sorted,
        'categories':     get_all_categories,
        'product_types':  lambda: get_all_product_types('name', 'asc'),
        'store_products': lambda: get_all_products('quantity', 'desc')
    }
    if table not in data_map:
        abort(404)

    data = data_map[table]()
    template = f'manager/report_tables/{table}.html'
    try:
        return render_template(template, data=data, today=date.today())
    except Exception:
        # підшаблону немає → 404
        abort(404)


# ═══════════════ 8. Сторінка звітів ═══════════════
@manager_bp.route('/reports')
def reports():
    """
    Сторінка з випадаючим списком таблиць та кнопками
    «Попередній перегляд» / «Друк». Сама логіка JS у шаблоні.
    """
    return render_template('manager/reports.html')

# ───────────────────── ЧЕКИ (17 + 18) ─────────────────────
@manager_bp.route('/receipts')
def receipts():
    # перелік касирів (тільки role='cashier')
    cashiers = [e for e in get_all_employees()
                if e['role'] == 'cashier']

    cashier_id = request.args.get('cashier') or None
    if cashier_id == 'all':
        cashier_id = None

    date_from  = request.args.get('from') or None
    date_to    = request.args.get('to')   or None
    sort_by    = request.args.get('sort_by', 'date')
    order      = request.args.get('order',   'desc')

    # перетворюємо дати
    try:
        d_from = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
    except ValueError:
        d_from = None
    try:
        d_to = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None
    except ValueError:
        d_to = None

    if cashier_id:
        receipts = get_checks_by_employee_period_mgr(
            cashier_id, d_from, d_to, sort_by, order
        )
    else:
        receipts = get_checks_all_period(
            d_from, d_to, sort_by, order
        )

    return render_template(
        'manager/receipts.html',
        receipts=receipts,
        cashiers=cashiers,
        cashier_id=cashier_id,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        order=order
    )


@manager_bp.route('/receipt/<check_number>')
def receipt_detail_mgr(check_number):
    details = get_check_details(check_number)
    if not details:
        abort(404)
    return render_template('cashier/receipt_detail.html', **details)

@manager_bp.route('/statistics')
def statistics():
    # список касирів лише з роллю 'cashier'
    cashiers = [e for e in get_all_employees() if e['role'] == 'cashier']

    # ── параметри GET ──────────────────────────────────────────
    cashier_id = request.args.get('cashier')           # id або 'all'
    if cashier_id in (None, 'all'):
        cashier_id = None

    period  = request.args.get('period', 'day')        # day|7d|month|year|all|custom
    ref_day = request.args.get('date')                 # YYYY-MM-DD
    upc_or_name = request.args.get('product') or None

    # якщо «глобальний» період all → ігноруємо дату
    if period == 'all':
        d_from = d_to = None
    else:
        # reference-date: сьогодні за замовчанням
        try:
            ref = datetime.strptime(ref_day, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            ref = date.today()

        periods = {
            'day': 1,
            '7d': 7,
            'month': 30,
            'year': 365
        }
        if period in periods:
            d_to = ref
            d_from = ref - timedelta(days=periods[period]-1)
        else:                 # «custom» – очікуємо date_from & date_to
            d_from = request.args.get('from')
            d_to   = request.args.get('to')
            def _parse(val):
                try: return datetime.strptime(val, "%Y-%m-%d").date()
                except Exception: return None
            d_from, d_to = _parse(d_from), _parse(d_to)

    # ── підрахунки ─────────────────────────────────────────────
    total_by_cashier = total_all = qty_sold = None
    chosen_product   = None

    if d_from or d_to or period == 'all':
        total_all = get_total_sales_all_period(d_from, d_to)
        if cashier_id:
            total_by_cashier = get_total_sales_by_cashier_period(
                cashier_id, d_from, d_to
            )

    if upc_or_name:
        prod_list = get_all_products(search=upc_or_name, search_field='upc')
        if not prod_list:
            prod_list = get_all_products(search=upc_or_name, search_field='name')
        if prod_list:
            chosen_product = prod_list[0]
            qty_sold = get_quantity_sold_period(
                chosen_product['upc'], d_from, d_to
            )

    # для автодоповнення
    products_for_js = get_all_products(sort_by='name', order='asc')

    return render_template(
        'manager/statistics.html',
        cashiers=cashiers,
        cashier_id=cashier_id,
        period=period,
        ref_day=ref.isoformat() if period != 'all' else '',
        d_from=d_from.isoformat() if d_from else '',
        d_to=d_to.isoformat()   if d_to   else '',
        product_input=upc_or_name,
        total_by_cashier=total_by_cashier,
        total_all=total_all,
        qty_sold=qty_sold,
        chosen_product=chosen_product,
        products=products_for_js
    )
