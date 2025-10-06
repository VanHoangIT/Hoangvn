"""
File Utils - Ưu tiên Cloudinary cho Production (Render/Heroku)
Local storage chỉ dùng khi dev và chưa config Cloudinary
"""
import os
import re
from datetime import datetime
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app
from app import db

# Cloudinary imports
try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api

    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False
    print("⚠️ WARNING: Cloudinary chưa cài đặt!")
    print("   pip install cloudinary")
    print("   Hiện tại chỉ dùng local storage (không khuyến nghị cho production)")


# ==================== COMMON UTILS ====================

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
        base_name = slugify(alt_text)
    else:
        base_name = slugify(name)

    # Giới hạn độ dài (max 50 ký tự)
    base_name = base_name[:50]

    # Thêm timestamp ngắn gọn
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    return f"{base_name}-{timestamp}{ext.lower()}"


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
        r'(ảnh|hình|image|picture|photo)\s*\d+',
        r'click\s+here',
        r'buy\s+now',
    ]

    for pattern in spam_patterns:
        if re.search(pattern, alt_text.lower()):
            return False, "Alt Text không nên chứa spam keywords"

    if alt_len >= 30 and alt_len <= 125:
        return True, "Alt Text đạt chuẩn SEO"
    else:
        return True, f"Alt Text hợp lệ nhưng nên 30-125 ký tự (hiện tại: {alt_len})"


# ==================== LOCAL STORAGE FUNCTIONS (Dev only) ====================

def get_image_dimensions(filepath):
    """Lấy kích thước ảnh"""
    try:
        with Image.open(filepath) as img:
            return img.size  # (width, height)
    except:
        return (0, 0)


def optimize_image(filepath, max_width=1920, max_height=1080, quality=85):
    """
    Tối ưu hóa ảnh cho web
    Returns: dict với thông tin ảnh sau khi tối ưu
    """
    try:
        with Image.open(filepath) as img:
            # Convert RGBA/LA/P sang RGB nếu cần
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            original_width, original_height = img.size

            # Resize nếu quá lớn
            if original_width > max_width or original_height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Lưu ảnh đã tối ưu
            img.save(filepath, 'JPEG', quality=quality, optimize=True, progressive=True)

            return {
                'width': img.size[0],
                'height': img.size[1],
                'format': 'JPEG',
                'optimized': True
            }

    except Exception as e:
        print(f"Error optimizing image: {e}")
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
    """Tạo thumbnail cho ảnh (chỉ dùng local)"""
    try:
        filename, ext = os.path.splitext(filepath)
        thumb_path = f"{filename}_thumb{ext}"

        with Image.open(filepath) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumb_path, quality=80)

        return thumb_path
    except:
        return None


def save_to_local(file, folder='general', album=None, alt_text=None, optimize=True):
    """
    Lưu file vào local storage (chỉ dev)
    ⚠️ WARNING: Không dùng trên Render/Heroku - file sẽ mất khi deploy
    Returns: (relative_path, file_info_dict)
    """
    if not file or not hasattr(file, 'filename') or not allowed_file(file.filename):
        return None, None

    filename = generate_seo_filename(file.filename, alt_text)

    # Xác định đường dẫn
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

    os.makedirs(upload_folder, exist_ok=True)

    # Lưu file
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # Tối ưu ảnh
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

    # Relative path
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
        'album': album,
        'storage': 'local'
    }

    return relative_path, file_info


# ==================== CLOUDINARY FUNCTIONS (Production) ====================

def upload_to_cloudinary(file, folder='general', public_id=None, optimize=True):
    """
    Upload file lên Cloudinary (khuyến nghị cho production)
    Returns: dict với thông tin file
    """
    if not CLOUDINARY_AVAILABLE:
        raise Exception("❌ Cloudinary chưa được cài đặt! pip install cloudinary")

    try:
        if not public_id:
            original_filename = getattr(file, 'filename', 'unnamed')
            name_without_ext = os.path.splitext(secure_filename(original_filename))[0]
            public_id = name_without_ext

        cloudinary_folder = f"aosmith/{folder}"

        upload_options = {
            'folder': cloudinary_folder,
            'public_id': public_id,
            'resource_type': 'auto',
            'overwrite': False,
            'unique_filename': True,
        }

        if optimize:
            upload_options.update({
                'quality': 'auto:good',
                'fetch_format': 'auto',
                'format': 'jpg',
            })
            upload_options['transformation'] = [
                {'width': 1920, 'height': 1200, 'crop': 'limit'},
                {'quality': 'auto:good'},
            ]

        result = cloudinary.uploader.upload(file, **upload_options)

        return {
            'url': result.get('url'),
            'secure_url': result.get('secure_url'),
            'public_id': result.get('public_id'),
            'format': result.get('format'),
            'width': result.get('width'),
            'height': result.get('height'),
            'bytes': result.get('bytes'),
            'resource_type': result.get('resource_type'),
            'created_at': result.get('created_at'),
            'storage': 'cloudinary'
        }

    except Exception as e:
        print(f"❌ Cloudinary upload error: {e}")
        raise


def delete_from_cloudinary(public_id):
    """Xóa file từ Cloudinary"""
    if not CLOUDINARY_AVAILABLE:
        return False
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        print(f"❌ Cloudinary delete error: {e}")
        return False


def extract_public_id(cloudinary_url):
    """
    Lấy public_id từ Cloudinary URL

    Examples:
        'https://res.cloudinary.com/demo/image/upload/v1234/aosmith/products/abc.jpg'
        -> 'aosmith/products/abc'
    """
    try:
        parts = cloudinary_url.split('/upload/')
        if len(parts) < 2:
            return None

        path = parts[1]
        if path.startswith('v'):
            path = '/'.join(path.split('/')[1:])

        public_id = os.path.splitext(path)[0]
        return public_id
    except Exception as e:
        print(f"❌ Error extracting public_id: {e}")
        return None


def get_cloudinary_url(public_id, transformation=None):
    """
    Tạo Cloudinary URL với transformation tùy chỉnh

    Args:
        public_id: 'aosmith/products/abc'
        transformation: dict hoặc list of dicts

    Examples:
        get_cloudinary_url('aosmith/products/abc', {'width': 300, 'crop': 'fill'})
        -> URL với ảnh 300px
    """
    try:
        url, options = cloudinary.utils.cloudinary_url(
            public_id,
            transformation=transformation,
            secure=True
        )
        return url
    except Exception as e:
        print(f"❌ Error generating URL: {e}")
        return None


def get_image_info(url_or_public_id):
    """Lấy thông tin chi tiết của ảnh từ Cloudinary"""
    try:
        if url_or_public_id.startswith('http'):
            public_id = extract_public_id(url_or_public_id)
        else:
            public_id = url_or_public_id

        if not public_id:
            return None

        result = cloudinary.api.resource(public_id)
        return result

    except Exception as e:
        print(f"❌ Error getting image info: {e}")
        return None


# ==================== UNIFIED INTERFACE ====================

def save_upload_file(file, folder='general', album=None, alt_text=None, optimize=True):
    """
    Lưu file - tự động chọn Cloudinary (production) hoặc local (dev)

    Priority:
    1. Cloudinary (nếu USE_CLOUDINARY=True) ✅ Khuyến nghị cho Render/Heroku
    2. Local fallback (nếu Cloudinary fail hoặc chưa config)

    Returns: (filepath_or_url, file_info_dict)
    """
    if not file or not hasattr(file, 'filename') or not allowed_file(file.filename):
        return None, None

    # Check config
    use_cloudinary = current_app.config.get('USE_CLOUDINARY', False)

    if use_cloudinary and CLOUDINARY_AVAILABLE:
        print("☁️  Uploading to Cloudinary (production mode)...")
        try:
            result = upload_to_cloudinary(file, folder=folder, optimize=optimize)
            print(f"✅ Upload thành công: {result['secure_url']}")
            return result['secure_url'], result
        except Exception as e:
            print(f"⚠️  Cloudinary failed: {e}")
            print("   → Fallback to local storage (file có thể mất sau khi deploy!)")
            return save_to_local(file, folder, album, alt_text, optimize)
    else:
        if use_cloudinary and not CLOUDINARY_AVAILABLE:
            print("⚠️  USE_CLOUDINARY=True nhưng chưa cài package!")
            print("   pip install cloudinary")

        print("💾 Uploading to local storage (dev mode)...")
        return save_to_local(file, folder, album, alt_text, optimize)


def delete_file(filepath_or_url):
    """
    Xóa file - tự động detect local hay Cloudinary
    """
    # Nếu là Cloudinary URL
    if filepath_or_url.startswith('http') and 'cloudinary' in filepath_or_url:
        print(f"☁️  Deleting from Cloudinary: {filepath_or_url}")
        public_id = extract_public_id(filepath_or_url)
        if public_id:
            result = delete_from_cloudinary(public_id)
            if result:
                print("✅ Deleted successfully")
            return result
        return False

    # Nếu là local file
    print(f"💾 Deleting from local storage: {filepath_or_url}")
    try:
        if filepath_or_url.startswith('/static/'):
            filepath_or_url = filepath_or_url.replace('/static/', '')

        full_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            '..',
            filepath_or_url
        )

        if os.path.exists(full_path):
            os.remove(full_path)
            print("✅ Deleted successfully")
            return True
    except Exception as e:
        print(f"❌ Error deleting file: {e}")
    return False


def get_image_from_form(form_image_field, field_name, folder='uploads'):
    """
    Lấy ảnh từ form - hỗ trợ cả upload mới và giữ ảnh cũ
    """
    file = form_image_field.data

    # Upload mới
    if file and hasattr(file, 'filename') and file.filename != '':
        relative_path, _ = save_upload_file(file, folder=folder, optimize=True)
        return relative_path

    # Giữ nguyên (URL cũ - có thể là Cloudinary hoặc local)
    if isinstance(file, str) and file.strip() != '':
        return file

    return None


def handle_image_upload(form_field, field_name, folder='general', alt_text=None):
    """
    Xử lý upload ảnh: ưu tiên từ media library, không thì upload mới
    """
    from flask import request

    # 1. Chọn từ media library
    selected_path = request.form.get(f'{field_name}_selected_path', '').strip()
    if selected_path:
        return selected_path

    # 2. Upload mới
    if form_field and hasattr(form_field, "filename") and form_field.filename:
        result = save_upload_file(form_field, folder=folder, alt_text=alt_text, optimize=True)
        return result[0] if isinstance(result, tuple) else result

    return None


# ==================== ALBUMS & MEDIA LIBRARY ====================

def get_albums():
    """Lấy danh sách albums (local storage only)"""
    from app.models import Media
    from sqlalchemy import func

    album_counts = db.session.query(
        Media.album,
        func.count(Media.id).label('count')
    ).filter(
        Media.album.isnot(None),
        Media.album != ''
    ).group_by(Media.album).all()

    albums_dict = {album_name: count for album_name, count in album_counts}

    # Thêm thư mục rỗng (chỉ có nghĩa với local storage)
    albums_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'albums')
    if os.path.exists(albums_path):
        for folder_name in os.listdir(albums_path):
            folder_path = os.path.join(albums_path, folder_name)
            if os.path.isdir(folder_path) and folder_name not in albums_dict:
                albums_dict[folder_name] = 0

    albums = [{'name': name, 'count': count} for name, count in albums_dict.items()]
    albums.sort(key=lambda x: x['name'])

    return albums


# ==================== MIGRATION TOOLS ====================

def migrate_local_to_cloudinary(local_filepath, folder='general'):
    """
    Migrate ảnh từ local lên Cloudinary
    Dùng để chuyển ảnh cũ từ local sang cloud khi deploy lên Render

    Usage:
        new_url = migrate_local_to_cloudinary('/static/uploads/products/abc.jpg', 'products')
    """
    if not CLOUDINARY_AVAILABLE:
        print("❌ Cloudinary chưa được cài đặt")
        return None

    try:
        if local_filepath.startswith('/static/'):
            local_filepath = local_filepath.replace('/static/', '')

        full_path = os.path.join(current_app.root_path, 'static', local_filepath)

        if not os.path.exists(full_path):
            print(f"❌ File không tồn tại: {full_path}")
            return None

        print(f"📤 Migrating {local_filepath} to Cloudinary...")
        with open(full_path, 'rb') as f:
            result = upload_to_cloudinary(f, folder=folder, optimize=True)

        print(f"✅ Migrated: {result['secure_url']}")
        return result['secure_url']

    except Exception as e:
        print(f"❌ Migration error: {e}")
        return None


def bulk_migrate_to_cloudinary(folder_type='products'):
    """
    Migrate toàn bộ ảnh trong 1 folder lên Cloudinary

    Usage:
        bulk_migrate_to_cloudinary('products')
    """
    from app.models import Media

    # Lấy tất cả media local
    local_media = Media.query.filter(
        ~Media.filepath.like('http%')  # Chưa phải URL Cloudinary
    ).all()

    migrated = 0
    failed = 0

    for media in local_media:
        try:
            new_url = migrate_local_to_cloudinary(media.filepath, folder_type)
            if new_url:
                media.filepath = new_url
                db.session.commit()
                migrated += 1
                print(f"✅ {media.filename}: {new_url}")
        except Exception as e:
            failed += 1
            print(f"❌ {media.filename}: {e}")

    print(f"\n🎉 Migration hoàn tất: {migrated} thành công, {failed} thất bại")
    return {'migrated': migrated, 'failed': failed}