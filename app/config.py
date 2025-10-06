import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()


class Config:
    """Cấu hình chung cho ứng dụng Flask"""

    # Secret key để mã hóa session và form CSRF
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Cấu hình database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), '../app.db')

    # Fix lỗi với Render PostgreSQL URL
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ==================== CLOUDINARY CONFIG ====================
    # Nếu có CLOUDINARY_URL thì dùng Cloudinary, không thì dùng local storage
    USE_CLOUDINARY = bool(os.environ.get('CLOUDINARY_URL'))

    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')
    CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')  # Format: cloudinary://api_key:api_secret@cloud_name

    # Cấu hình upload file (dùng cho local fallback)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Max 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Pagination
    POSTS_PER_PAGE = 12
    BLOGS_PER_PAGE = 9

    # SEO
    SITE_NAME = 'Hoangvn'
    SITE_DESCRIPTION = 'Website doanh nghiệp chuyên nghiệp'

    @staticmethod
    def init_app(app):
        """Khởi tạo cấu hình cho app"""
        # Tạo thư mục upload nếu chưa tồn tại (cho local storage)
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)

        # Tạo các thư mục con
        for folder in ['products', 'banners', 'blogs', 'categories', 'albums', 'projects']:
            os.makedirs(os.path.join(upload_folder, folder), exist_ok=True)

        # Khởi tạo Cloudinary nếu có config
        if app.config.get('USE_CLOUDINARY'):
            import cloudinary
            cloudinary.config(
                cloud_name=app.config.get('CLOUDINARY_CLOUD_NAME'),
                api_key=app.config.get('CLOUDINARY_API_KEY'),
                api_secret=app.config.get('CLOUDINARY_API_SECRET'),
                secure=True
            )
            print("✓ Cloudinary đã được kích hoạt!")
        else:
            print("ℹ Đang dùng local storage (chưa config Cloudinary)")