from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange

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
