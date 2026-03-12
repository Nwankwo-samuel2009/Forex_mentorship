# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from models import User  # This line should work now


class RegistrationForm(FlaskForm):
    """User registration form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered.')


class LoginForm(FlaskForm):
    """User login form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class ContactForm(FlaskForm):
    """Contact form"""
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired(), Length(min=2, max=200)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Send Message')


class MentorshipApplicationForm(FlaskForm):
    """Mentorship application form"""
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number (Optional)', validators=[Length(max=20)])
    experience_level = SelectField('Trading Experience',
                                   choices=[('beginner', 'Beginner (0-6 months)'),
                                            ('intermediate', 'Intermediate (6 months - 2 years)'),
                                            ('advanced', 'Advanced (2+ years)')],
                                   validators=[DataRequired()])
    trading_style = SelectField('Preferred Trading Style',
                                choices=[('day', 'Day Trading'),
                                         ('swing', 'Swing Trading'),
                                         ('scalping', 'Scalping'),
                                         ('position', 'Position Trading'),
                                         ('unsure', 'Not Sure Yet')],
                                validators=[DataRequired()])
    goals = TextAreaField('What are your trading goals?', validators=[DataRequired(), Length(min=20)])
    message = TextAreaField('Additional Information (Optional)')
    submit = SubmitField('Apply Now')


class PostForm(FlaskForm):
    """Blog post form (admin only)"""
    title = StringField('Title', validators=[DataRequired(), Length(min=5, max=100)])
    summary = StringField('Summary', validators=[DataRequired(), Length(min=10, max=200)])
    content = TextAreaField('Content', validators=[DataRequired(), Length(min=50)])
    submit = SubmitField('Post')