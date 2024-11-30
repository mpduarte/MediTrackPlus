from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, IntegerField, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, NumberRange
from models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField(
        'Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose another one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use another one.')

class MedicationForm(FlaskForm):
    name = StringField('Medication Name', validators=[DataRequired()])
    dosage = StringField('Dosage', validators=[DataRequired()])
    frequency = SelectField('Frequency', 
                          choices=[('daily', 'Daily'), 
                                 ('twice_daily', 'Twice Daily'),
                                 ('weekly', 'Weekly')],
                          validators=[DataRequired()])
    current_stock = IntegerField('Current Stock', validators=[DataRequired(), NumberRange(min=0)])
    scheduled_time = StringField('Scheduled Time')
    max_daily_doses = IntegerField('Maximum Daily Doses', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Add Medication')

class InventoryUpdateForm(FlaskForm):
    quantity = IntegerField('Quantity Change (+/-)', validators=[DataRequired()])
    submit = SubmitField('Update Stock')

class ConsumptionForm(FlaskForm):
    quantity = IntegerField('Quantity', default=1, validators=[DataRequired(), NumberRange(min=1)])
    status = SelectField('Status', choices=[('taken', 'Taken'), ('missed', 'Missed'), ('skipped', 'Skipped')])
    submit = SubmitField('Log Dose')

class PrescriptionForm(FlaskForm):
    prescription_file = FileField('Prescription Image', 
                                validators=[FileRequired(),
                                          FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Images and PDF only!')])
    expiry_date = DateField('Expiry Date', format='%Y-%m-%d')
    notes = TextAreaField('Notes')
    submit = SubmitField('Upload Prescription')