from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Regexp, NumberRange
from models import User

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', message='Usernames must start with a letter and can only contain letters, numbers, dots or underscores')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class MedicationForm(FlaskForm):
    name = StringField('Medication Name', validators=[DataRequired()])
    dosage = StringField('Dosage', validators=[DataRequired()])
    frequency = SelectField('Frequency', 
                          choices=[('daily', 'Daily'),
                                 ('twice_daily', 'Twice Daily'),
                                 ('weekly', 'Weekly')],
                          validators=[DataRequired()])
    current_stock = IntegerField('Current Stock', 
                               validators=[DataRequired(), 
                                         NumberRange(min=0)])
    submit = SubmitField('Add Medication')

class ConsumptionForm(FlaskForm):
    quantity = IntegerField('Quantity', 
                          validators=[DataRequired(), 
                                    NumberRange(min=1)])
    submit = SubmitField('Log Consumption')

class InventoryUpdateForm(FlaskForm):
    quantity = IntegerField('Quantity', 
                          validators=[DataRequired(), 
                                    NumberRange(min=1)])
    submit = SubmitField('Update Inventory')
