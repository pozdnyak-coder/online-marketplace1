import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Product, CartItem, Review
from forms import RegistrationForm, LoginForm, ProductForm, ReviewForm
import logging
logging.basicConfig(level=logging.DEBUG)

# --- Настройка приложения ---
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# --- Настройка базы данных (PostgreSQL для Vercel) ---
# Получаем строку подключения из переменной окружения
database_url = os.environ.get('DATABASE_URL', 'sqlite:///marketplace.db')
# SQLAlchemy требует postgresql://, а Render/Neon иногда дают postgres://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# --- Настройка Flask-Login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Создание таблиц (для serverless окружения) ---
# В Vercel функции могут запускаться в разных инстансах, поэтому создаём таблицы
# перед первым запросом, если их ещё нет.
with app.app_context():
    db.create_all()

# --- Маршруты (страницы) приложения ---

@app.route('/')
def index():
    """Главная страница с каталогом товаров и фильтрами."""
    products = db.session.query(Product).join(User).filter(User.is_seller == True)
    category = request.args.get('category')
    search = request.args.get('search')

    if category and category != 'all':
        products = products.filter(Product.category == category)
    if search:
        products = products.filter(Product.name.contains(search) | Product.description.contains(search))

    products = products.all()
    return render_template('index.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации нового пользователя."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            is_seller=form.is_seller.data
        )
        db.session.add(user)
        db.session.commit()
        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа в систему."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Выход из системы."""
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Страница с детальной информацией о товаре и отзывами."""
    product = Product.query.get_or_404(product_id)
    form = ReviewForm()
    return render_template('product_detail.html', product=product, form=form)

@app.route('/product/<int:product_id>/review', methods=['POST'])
@login_required
def add_review(product_id):
    """Обработчик для добавления отзыва о товаре."""
    product = Product.query.get_or_404(product_id)
    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            user_id=current_user.id,
            product_id=product.id,
            rating=int(form.rating.data),
            comment=form.comment.data
        )
        db.session.add(review)
        db.session.commit()
        flash('Ваш отзыв добавлен!', 'success')
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    """Страница для добавления нового товара (только для продавцов)."""
    if not current_user.is_seller:
        flash('Только продавцы могут добавлять товары.', 'danger')
        return redirect(url_for('index'))
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            category=form.category.data,
            stock=form.stock.data,
            seller_id=current_user.id
        )
        db.session.add(product)
        db.session.commit()
        flash('Товар успешно добавлен!', 'success')
        return redirect(url_for('my_products'))
    return render_template('add_product.html', form=form)

@app.route('/my_products')
@login_required
def my_products():
    """Страница со списком товаров, добавленных текущим продавцом."""
    if not current_user.is_seller:
        flash('Только продавцы могут просматривать эту страницу.', 'danger')
        return redirect(url_for('index'))
    products = Product.query.filter_by(seller_id=current_user.id).all()
    return render_template('my_products.html', products=products)

@app.route('/add_to_cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    """Добавление товара в корзину."""
    product = Product.query.get_or_404(product_id)
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(cart_item)
    db.session.commit()
    flash(f'{product.name} добавлен в корзину!', 'success')
    return redirect(url_for('index'))

@app.route('/cart')
@login_required
def cart():
    """Страница корзины пользователя."""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/update_cart/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    """Обновление количества товара в корзине."""
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    data = request.get_json()
    new_quantity = int(data.get('quantity', 1))
    if new_quantity > 0:
        item.quantity = new_quantity
        db.session.commit()
    return jsonify({'success': True, 'new_total': item.quantity * item.product.price})

@app.route('/remove_from_cart/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    """Удаление товара из корзины."""
    item = CartItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
        flash('Товар удален из корзины.', 'info')
    return redirect(url_for('cart'))

@app.route('/checkout')
@login_required
def checkout():
    """Оформление заказа."""
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Ваша корзина пуста.', 'warning')
        return redirect(url_for('index'))
    for item in cart_items:
        product = item.product
        if product.stock >= item.quantity:
            product.stock -= item.quantity
            db.session.delete(item)
        else:
            flash(f'К сожалению, товара "{product.name}" недостаточно на складе.', 'danger')
            db.session.rollback()
            return redirect(url_for('cart'))
    db.session.commit()
    flash('Заказ успешно оформлен! Спасибо за покупку.', 'success')
    return redirect(url_for('index'))

# --- Точка входа для Vercel (serverless) ---
# Vercel ожидает объект `app`, поэтому этот блок не обязателен, но оставим для локального запуска.
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
