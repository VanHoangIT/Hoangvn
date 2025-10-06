import os
import re
from datetime import datetime
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app
from app import db


def allowed_file(filename):
    """Kiểm tra file có hợp lệ không"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def slugify(text):
    """
    Chuyển text thành slug SEO-friendly
    VD: "Máy lọc nước A.O.Smith" -> "may-loc-nuoc-aosmith"
    """
    text = text.lower()
    # Chuyển tiếng Việt không dấu
    text = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', text)
    text = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', text)
    text = re.sub(r'[ìíịỉĩ]', 'i', text)
    text = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', text)
    text = re.sub(r'[ùúụủũưừứựửữ]', 'u', text)
    text = re.sub(r'[ỳýỵỷỹ]', 'y', text)
    text = re.sub(r'[đ]', 'd', text)
    # Xóa ký tự đặc biệt
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # Thay space bằng dash
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')


def generate_seo_filename(original_filename, alt_text=None):
    """
    Tạo tên file SEO-friendly
    - Ưu tiên dùng alt_text nếu có
    - Loại bỏ ký tự đặc biệt
    - Thêm timestamp để tránh trùng
    """
    name, ext = os.path.splitext(original_filename)

    if alt_text:
        # Sử dụng alt_text làm tên file
        base_name = slugify(alt_text)
    else:
        # Sử dụng tên gốc
        base_name = slugify(name)

    # Giới hạn độ dài (max 50 ký tự)
    base_name = base_name[:50]

    # Thêm timestamp ngắn gọn
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    return f"{base_name}-{timestamp}{ext.lower()}"


def get_image_dimensions(filepath):
    """Lấy kích thước ảnh"""
    try:
        with Image.open(filepath) as img:
            return img.size  # (width, height)
    except:
        return (0, 0)


def optimize_image(filepath, max_width=1920, max_height=1080, quality=85):
    """
    Tối ưu hóa ảnh cho web và SEO:
    - Resize về kích thước phù hợp (giữ tỷ lệ)
    - Nén với quality tối ưu
    - Convert sang Progressive JPEG (load nhanh hơn)
    - Loại bỏ EXIF data không cần thiết

    Returns: dict với thông tin ảnh sau khi tối ưu
    """
    try:
        with Image.open(filepath) as img:
            # Convert RGBA/LA/P sang RGB nếu cần (cho JPEG)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            # Lấy kích thước gốc
            original_width, original_height = img.size

            # Resize nếu quá lớn (giữ tỷ lệ aspect ratio)
            if original_width > max_width or original_height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Lưu ảnh đã tối ưu
            # Progressive JPEG giúp ảnh load nhanh hơn trên web
            img.save(filepath, 'JPEG', quality=quality, optimize=True, progressive=True)

            # Trả về thông tin ảnh sau khi tối ưu
            return {
                'width': img.size[0],
                'height': img.size[1],
                'format': 'JPEG',
                'optimized': True
            }

    except Exception as e:
        print(f"Error optimizing image: {e}")
        # Nếu optimize fail, vẫn lấy kích thước gốc
        try:
            width, height = get_image_dimensions(filepath)
            return {
                'width': width,
                'height': height,
                'format': 'Unknown',
                'optimized': False
            }
        except:
            return None


def create_thumbnail(filepath, size=(300, 300)):
    """Tạo thumbnail cho ảnh"""
    try:
        filename, ext = os.path.splitext(filepath)
        thumb_path = f"{filename}_thumb{ext}"

        with Image.open(filepath) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumb_path, quality=80)

        return thumb_path
    except:
        return None

def get_image_from_form(form_image_field, field_name, folder='uploads'):
    file = form_image_field.data

    # Trường hợp 1: có file upload mới (FileStorage object)
    if file and hasattr(file, 'filename') and file.filename != '':
        relative_path, _ = save_upload_file(file, folder=folder, optimize=True)
        return relative_path

    # Trường hợp 2: giữ nguyên string (đường dẫn cũ trong DB)
    if isinstance(file, str) and file.strip() != '':
        return file

    return None



def save_upload_file(file, folder='general', album=None, alt_text=None, optimize=True):
    """
    Lưu file upload với đầy đủ tính năng SEO:
    - folder: thư mục đích (products, banners, blogs)
    - album: tên album/thư mục con tùy chỉnh
    - alt_text: Alt text cho tên file SEO-friendly
    - optimize: có tối ưu ảnh không

    Returns: (relative_path, file_info_dict) or (None, None)
    """
    if not file or not hasattr(file, 'filename') or not allowed_file(file.filename):
        return None, None

    # Tạo tên file SEO-friendly
    filename = generate_seo_filename(file.filename, alt_text)

    # Xác định đường dẫn lưu
    if album:
        upload_folder = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            'albums',
            secure_filename(album)
        )
    else:
        year_month = datetime.now().strftime('%Y-%m')
        upload_folder = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            folder,
            year_month
        )

    # Tạo thư mục nếu chưa có
    os.makedirs(upload_folder, exist_ok=True)

    # Lưu file
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # Lấy kích thước và tối ưu ảnh
    width, height = 0, 0
    if optimize and file.content_type and file.content_type.startswith('image/'):
        max_widths = {
            'banners': 1920,
            'products': 800,
            'blogs': 1200,
            'categories': 600,
            'general': 1920
        }
        max_width = max_widths.get(folder, 1920)

        result = optimize_image(filepath, max_width=max_width)
        if result:
            width = result['width']
            height = result['height']
    else:
        width, height = get_image_dimensions(filepath)

    file_size = os.path.getsize(filepath)

    # Tạo relative path để serve qua /static/
    relative_path = filepath.replace(
        current_app.config['UPLOAD_FOLDER'],
        '/static/uploads'
    ).replace('\\', '/')

    file_info = {
        'filename': filename,
        'original_filename': file.filename,
        'filepath': relative_path,
        'file_type': file.content_type,
        'file_size': file_size,
        'width': width,
        'height': height,
        'album': album
    }

    return relative_path, file_info


def delete_file(filepath):
    """Xóa file khỏi server"""
    try:
        # Convert relative path to absolute
        if filepath.startswith('/static/'):
            filepath = filepath.replace('/static/', '')

        full_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            '..',
            filepath
        )

        if os.path.exists(full_path):
            os.remove(full_path)
            return True
    except Exception as e:
        print(f"Error deleting file: {e}")
    return False


def get_albums():
    """Lấy danh sách albums với số lượng file"""
    from app.models import Media
    from sqlalchemy import func

    # Lấy albums từ DB
    album_counts = db.session.query(
        Media.album,
        func.count(Media.id).label('count')
    ).filter(
        Media.album.isnot(None),
        Media.album != ''
    ).group_by(Media.album).all()

    albums_dict = {album_name: count for album_name, count in album_counts}

    # Lấy thư mục vật lý (kể cả rỗng)
    albums_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'albums')
    if os.path.exists(albums_path):
        for folder_name in os.listdir(albums_path):
            folder_path = os.path.join(albums_path, folder_name)
            if os.path.isdir(folder_path) and folder_name not in albums_dict:
                albums_dict[folder_name] = 0

    # Convert sang list và sort
    albums = [{'name': name, 'count': count} for name, count in albums_dict.items()]
    albums.sort(key=lambda x: x['name'])

    return albums


def handle_image_upload(form_field, field_name, folder='general', alt_text=None):
    """
    Xử lý upload ảnh: ưu tiên từ media library, không thì upload mới

    Args:
        form_field: File từ form (có thể None)
        field_name: Tên field để lấy path từ hidden input
        folder: Thư mục lưu nếu upload mới
        alt_text: Alt text cho SEO (optional)

    Returns:
        str: Đường dẫn ảnh hoặc None
    """
    from flask import request

    # 1. Kiểm tra có chọn từ media library không
    selected_path = request.form.get(f'{field_name}_selected_path', '').strip()
    if selected_path:
        return selected_path

    # 2. Nếu không, upload file mới
    if form_field and hasattr(form_field, "filename") and form_field.filename:
        result = save_upload_file(form_field, folder=folder, alt_text=alt_text, optimize=True)
        return result[0] if isinstance(result, tuple) else result

    # 3. Không có gì cả
    return None


def validate_seo_alt_text(alt_text):
    """
    Validate Alt Text theo chuẩn SEO

    Returns: (is_valid, message)
    """
    if not alt_text or len(alt_text.strip()) == 0:
        return False, "Alt Text không được để trống"

    alt_len = len(alt_text)

    if alt_len < 10:
        return False, f"Alt Text quá ngắn ({alt_len} ký tự). Nên từ 30-125 ký tự"

    if alt_len > 125:
        return False, f"Alt Text quá dài ({alt_len} ký tự). Nên từ 30-125 ký tự"

    # Check spam keywords
    spam_patterns = [
        r'(ảnh|hình|image|picture|photo)\s*\d+',  # ảnh 1, image123
        r'click\s+here',
        r'buy\s+now',
    ]

    for pattern in spam_patterns:
        if re.search(pattern, alt_text.lower()):
            return False, "Alt Text không nên chứa spam keywords như 'ảnh 123', 'click here'"

    if alt_len >= 30 and alt_len <= 125:
        return True, "Alt Text đạt chuẩn SEO"
    else:
        return True, f"Alt Text hợp lệ nhưng nên 30-125 ký tự (hiện tại: {alt_len})"