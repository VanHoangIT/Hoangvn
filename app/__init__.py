from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from app.config import Config
import cloudinary
import os

# Khởi tạo extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app(config_class=Config):
    """Factory function để tạo Flask app"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Khởi tạo extensions với app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Cấu hình Flask-Login
    login_manager.login_view = 'admin.login'  # Redirect đến trang login nếu chưa đăng nhập
    login_manager.login_message = 'Vui lòng đăng nhập để truy cập trang này.'
    login_manager.login_message_category = 'warning'

    # Import models (để Flask-Migrate nhận diện)
    from app import models

    # Đăng ký blueprints
    from app.main.routes import main_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Khởi tạo cấu hình
    config_class.init_app(app)

    # Context processor - biến toàn cục cho templates
    @app.context_processor
    def inject_globals():
        from app.models import Category
        return {
            'site_name': app.config['SITE_NAME'],
            'all_categories': Category.query.filter_by(is_active=True).all()
        }

    # Custom Jinja2 filters
    @app.template_filter('format_price')
    def format_price(value):
        """Format giá tiền: 1000000 -> 1.000.000"""
        if value:
            return '{:,.0f}'.format(value).replace(',', '.')
        return '0'

    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Convert newlines to <br> tags"""
        if not text:
            return ''
        return text.replace('\n', '<br>\n')

    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET'),
        secure=True
    )

    return app