from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from ...utils.db import get_db

cashier_bp = Blueprint(
    'cashier',
    __name__,
    url_prefix='/cashier'
)

@cashier_bp.route('/dashboard')
def dashboard():
    return render_template('cashier/dashboard.html')

# Додайте сюди інші роут-функції:
# @cashier_bp.route('/products')     -> render_template('cashier/products.html')
# @cashier_bp.route('/customers')    -> render_template('cashier/customers.html')
# @cashier_bp.route('/create_receipt', methods=['GET','POST']) -> render_template('cashier/create_receipt.html')
# @cashier_bp.route('/my_receipts')  -> render_template('cashier/my_receipts.html')
