# app.py
from flask import Flask, render_template, url_for, flash, redirect, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from flask_mail import Mail, Message
from datetime import datetime
import os
from forms import RegistrationForm, LoginForm, ContactForm, PostForm, MentorshipApplicationForm
from models import db, bcrypt, User, Post, ContactMessage, MentorshipApplication, PortfolioItem, TradingResult

# Initialize app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail configuration (Update with your email settings)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS', 'your-password')
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)
mail = Mail(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes
@app.route('/')
def index():
    """Home page"""
    recent_posts = Post.query.order_by(Post.date_posted.desc()).limit(3).all()
    portfolio_items = PortfolioItem.query.filter_by(show_on_home=True).limit(4).all()
    return render_template('index.html',
                           recent_posts=recent_posts,
                           portfolio_items=portfolio_items)


@app.route('/about')
def about():
    """About me page"""
    return render_template('about.html')


@app.route('/portfolio')
def portfolio():
    """Trading portfolio/results page"""
    portfolio_items = PortfolioItem.query.order_by(PortfolioItem.date.desc()).all()
    trading_results = TradingResult.query.order_by(TradingResult.date.desc()).all()

    # Calculate statistics
    total_trades = len(trading_results)
    winning_trades = sum(1 for r in trading_results if r.profit_loss > 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_profit = sum(r.profit_loss for r in trading_results)

    return render_template('portfolio.html',
                           portfolio_items=portfolio_items,
                           trading_results=trading_results,
                           total_trades=total_trades,
                           win_rate=win_rate,
                           total_profit=total_profit)


@app.route('/mentorship', methods=['GET', 'POST'])
def mentorship():
    """Mentorship program page"""
    form = MentorshipApplicationForm()

    if form.validate_on_submit():
        application = MentorshipApplication(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            experience_level=form.experience_level.data,
            trading_style=form.trading_style.data,
            goals=form.goals.data,
            message=form.message.data
        )

        db.session.add(application)
        db.session.commit()

        # Send email notification
        send_mentorship_notification(application)

        flash('Your application has been submitted! I will contact you within 24-48 hours.', 'success')
        return redirect(url_for('mentorship'))

    return render_template('mentorship.html', form=form)


@app.route('/blog')
def blog():
    """Blog posts listing"""
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('blog.html', posts=posts)


@app.route('/post/<int:post_id>')
def post(post_id):
    """Individual blog post"""
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    form = ContactForm()

    if form.validate_on_submit():
        message = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            subject=form.subject.data,
            message=form.message.data
        )

        db.session.add(message)
        db.session.commit()

        # Send email notification
        send_contact_notification(message)

        flash('Your message has been sent! I will get back to you soon.', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data,
                    email=form.email.data,
                    password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Check email and password.', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    """User logout"""
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard for mentors/students"""
    if current_user.is_mentor:
        # Mentor dashboard
        pending_applications = MentorshipApplication.query.filter_by(status='pending').count()
        recent_messages = ContactMessage.query.order_by(ContactMessage.date_sent.desc()).limit(5).all()
        return render_template('dashboard.html',
                               pending_applications=pending_applications,
                               recent_messages=recent_messages)
    else:
        # Student dashboard
        applications = MentorshipApplication.query.filter_by(email=current_user.email).all()
        return render_template('dashboard.html', applications=applications)


# Admin routes
@app.route('/admin/posts')
@login_required
def admin_posts():
    """Manage blog posts (admin only)"""
    if not current_user.is_mentor:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('admin/posts.html', posts=posts)


@app.route('/admin/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    """Create new blog post (admin only)"""
    if not current_user.is_mentor:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    form = PostForm()
    if form.validate_on_submit():
        post = Post(
            title=form.title.data,
            content=form.content.data,
            summary=form.summary.data,
            author=current_user
        )
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('admin_posts'))

    return render_template('create_post.html', form=form, legend='New Post')


@app.route('/admin/post/<int:post_id>/update', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    """Update blog post (admin only)"""
    if not current_user.is_mentor:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    post = Post.query.get_or_404(post_id)
    form = PostForm()

    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.summary = form.summary.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('admin_posts'))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
        form.summary.data = post.summary

    return render_template('create_post.html', form=form, legend='Update Post')


@app.route('/admin/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    """Delete blog post (admin only)"""
    if not current_user.is_mentor:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('admin_posts'))


@app.route('/admin/messages')
@login_required
def admin_messages():
    """View contact messages (admin only)"""
    if not current_user.is_mentor:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    messages = ContactMessage.query.order_by(ContactMessage.date_sent.desc()).all()
    return render_template('admin/messages.html', messages=messages)


@app.route('/admin/applications')
@login_required
def admin_applications():
    """View mentorship applications (admin only)"""
    if not current_user.is_mentor:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    applications = MentorshipApplication.query.order_by(MentorshipApplication.date_applied.desc()).all()
    return render_template('admin/applications.html', applications=applications)


@app.route('/admin/application/<int:app_id>/update-status', methods=['POST'])
@login_required
def update_application_status(app_id):
    """Update mentorship application status"""
    if not current_user.is_mentor:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    application = MentorshipApplication.query.get_or_404(app_id)
    status = request.form.get('status')

    if status in ['pending', 'contacted', 'accepted', 'rejected']:
        application.status = status
        db.session.commit()
        flash(f'Application status updated to {status}.', 'success')

    return redirect(url_for('admin_applications'))


# Helper functions for email notifications
def send_contact_notification(message):
    """Send email notification for contact form"""
    try:
        msg = Message(f'New Contact Message: {message.subject}',
                      recipients=[app.config['MAIL_USERNAME']])
        msg.body = f"""
        Name: {message.name}
        Email: {message.email}
        Subject: {message.subject}

        Message:
        {message.message}
        """
        mail.send(msg)
    except Exception as e:
        print(f"Email error: {e}")


def send_mentorship_notification(application):
    """Send email notification for mentorship application"""
    try:
        msg = Message('New Mentorship Application',
                      recipients=[app.config['MAIL_USERNAME']])
        msg.body = f"""
        New Mentorship Application Received:

        Name: {application.name}
        Email: {application.email}
        Phone: {application.phone}
        Experience Level: {application.experience_level}
        Trading Style: {application.trading_style}

        Goals:
        {application.goals}

        Additional Message:
        {application.message}
        """
        mail.send(msg)
    except Exception as e:
        print(f"Email error: {e}")


# Create tables
with app.app_context():
    db.create_all()

    # Create admin user if not exists
    if not User.query.filter_by(email='admin@example.com').first():
        hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin = User(
            username='admin',
            email='admin@example.com',
            password=hashed_password,
            is_mentor=True
        )
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)