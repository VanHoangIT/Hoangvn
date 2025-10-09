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

    # ✅ ========== BẮT ĐẦU CODE MỚI ==========
    # Inject get_setting vào tất cả templates
    from app.models import get_setting

    @app.context_processor
    def inject_global_settings():
        """
        Inject settings vào mọi template
        Không cần truyền qua render_template nữa
        """
        return {
            'get_setting': get_setting,
            # Pre-load các settings thường dùng
            'primary_color': get_setting('primary_color', '#ffc107'),
            'default_banner': get_setting('default_banner', ''),
            'per_page': int(get_setting('default_posts_per_page', '12')),
            'contact_intro': get_setting('contact_form', ''),
        }

    # ✅ ========== KẾT THÚC CODE MỚI ==========

    # Cấu hình Flask-Login
    login_manager.login_view = 'admin.login'
    login_manager.login_message = 'Vui lòng đăng nhập để truy cập trang này.'
    login_manager.login_message_category = 'warning'

    # Đăng ký blueprints
    from app.main.routes import main_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # ========== THÊM MỚI: Đăng ký chatbot blueprint ==========
    from app.chatbot import chatbot_bp
    app.register_blueprint(chatbot_bp)

    # Khởi tạo Gemini sau khi app được tạo
    with app.app_context():
        from app.chatbot.routes import init_gemini
        init_gemini()

    # Khởi tạo cấu hình
    config_class.init_app(app)

    # ==================== CONTEXT PROCESSOR - BIẾN TOÀN CỤC ====================
    @app.context_processor
    def inject_globals():
        """
        Inject các biến toàn cục vào tất cả templates
        - get_setting: Function để lấy settings từ DB
        - site_name: Tên website
        - all_categories: Danh sách categories
        - current_year: Năm hiện tại
        """
        from app.models import Category, get_setting as db_get_setting
        from datetime import datetime

        return {
            'get_setting': db_get_setting,  # ✅ THÊM FUNCTION get_setting
            'site_name': app.config.get('SITE_NAME', 'Hoangvn'),
            'all_categories': Category.query.filter_by(is_active=True).all(),
            'current_year': datetime.now().year  # ✅ Lấy năm động thay vì hardcode
        }

    # ==================== CUSTOM JINJA2 FILTERS ====================
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

    # ==================== CẤU HÌNH CLOUDINARY ====================
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET'),
        secure=True
    )

    return app