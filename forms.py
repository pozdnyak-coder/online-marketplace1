from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, FloatField, IntegerField, SelectField
from wtforms.validators import InputRequired, Email, Length, NumberRange

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[InputRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Пароль', validators=[InputRequired(), Length(min=6)])
    is_seller = BooleanField('Зарегистрироваться как продавец')

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[InputRequired()])
    password = PasswordField('Пароль', validators=[InputRequired()])

class ProductForm(FlaskForm):
    name = StringField('Название товара', validators=[InputRequired()])
    description = TextAreaField('Описание', validators=[InputRequired()])
    price = FloatField('Цена', validators=[InputRequired(), NumberRange(min=0.01)])
    category = SelectField('Категория', choices=[
        ('electronics', 'Электроника'),
        ('clothing', 'Одежда'),
        ('books', 'Книги'),
        ('home', 'Дом'),
        ('other', 'Другое')
    ], validators=[InputRequired()])
    stock = IntegerField('Количество', validators=[InputRequired(), NumberRange(min=1)])

class ReviewForm(FlaskForm):
    rating = SelectField('Оценка', choices=[(str(i), str(i)) for i in range(1,6)], validators=[InputRequired()])
    comment = TextAreaField('Отзыв', validators=[InputRequired(), Length(min=10)])
