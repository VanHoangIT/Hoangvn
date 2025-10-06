"""
Cloudinary utility functions
Xử lý upload, delete, optimize ảnh lên Cloudinary
"""
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import current_app
from werkzeug.utils import secure_filename
from PIL import Image
import io


def upload_to_cloudinary(file, folder='general', public_id=None, optimize=True):
    """
    Upload file lên Cloudinary

    Args:
        file: FileStorage object hoặc file path
        folder: Thư mục trên Cloudinary (vd: 'products', 'blogs')
        public_id: Tên file tùy chỉnh (không bao gồm extension)
        optimize: Tự động optimize ảnh

    Returns:
        dict: {
            'url': 'https://res.cloudinary.com/...',
            'secure_url': 'https://...',
            'public_id': 'folder/filename',
            'format': 'jpg',
            'width': 1920,
            'height': 1080,
            'bytes': 245678,
            'resource_type': 'image'
        }
    """
    try:
        # Tạo public_id nếu chưa có
        if not public_id:
            original_filename = getattr(file, 'filename', 'unnamed')
            name_without_ext = os.path.splitext(secure_filename(original_filename))[0]
            public_id = name_without_ext

        # Cloudinary folder path
        cloudinary_folder = f"aosmith/{folder}"

        # Upload options
        upload_options = {
            'folder': cloudinary_folder,
            'public_id': public_id,
            'resource_type': 'auto',
            'overwrite': False,
            'unique_filename': True,  # Thêm suffix nếu trùng tên
        }

        # Optimize options
        if optimize:
            upload_options.update({
                'quality': 'auto:good',  # Tự động optimize chất lượng
                'fetch_format': 'auto',  # Tự động chọn format tốt nhất (WebP cho browser hỗ trợ)
                'format': 'jpg',  # Default format
            })

            # Resize nếu ảnh quá lớn
            upload_options['transformation'] = [
                {'width': 1920, 'height': 1200, 'crop': 'limit'},  # Max size
                {'quality': 'auto:good'},
            ]

        # Upload lên Cloudinary
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
        }

    except Exception as e:
        print(f"❌ Cloudinary upload error: {e}")
        raise


def delete_from_cloudinary(public_id):
    """
    Xóa file từ Cloudinary

    Args:
        public_id: Public ID của file (vd: 'aosmith/products/abc123')

    Returns:
        bool: True nếu xóa thành công
    """
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
        # URL format: https://res.cloudinary.com/{cloud_name}/{resource_type}/upload/{version}/{public_id}.{format}
        parts = cloudinary_url.split('/upload/')
        if len(parts) < 2:
            return None

        # Lấy phần sau /upload/
        path = parts[1]

        # Bỏ version number (vXXXX/)
        if path.startswith('v'):
            path = '/'.join(path.split('/')[1:])

        # Bỏ extension
        public_id = os.path.splitext(path)[0]

        return public_id
    except Exception as e:
        print(f"❌ Error extracting public_id: {e}")
        return None


def get_cloudinary_url(public_id, transformation=None):
    """
    Tạo Cloudinary URL với transformation

    Args:
        public_id: 'aosmith/products/abc'
        transformation: dict hoặc list of dicts

    Examples:
        get_cloudinary_url('aosmith/products/abc', {'width': 300, 'crop': 'fill'})
        -> https://res.cloudinary.com/.../w_300,c_fill/aosmith/products/abc.jpg
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


def migrate_local_to_cloudinary(local_filepath, folder='general'):
    """
    Migrate 1 ảnh từ local lên Cloudinary

    Args:
        local_filepath: '/static/uploads/products/abc.jpg'
        folder: 'products'

    Returns:
        str: Cloudinary URL mới
    """
    try:
        # Convert relative path to absolute
        if local_filepath.startswith('/static/'):
            local_filepath = local_filepath.replace('/static/', '')

        full_path = os.path.join(current_app.root_path, 'static', local_filepath)

        if not os.path.exists(full_path):
            print(f"❌ File không tồn tại: {full_path}")
            return None

        # Upload lên Cloudinary
        with open(full_path, 'rb') as f:
            result = upload_to_cloudinary(f, folder=folder, optimize=True)

        return result['secure_url']

    except Exception as e:
        print(f"❌ Migration error: {e}")
        return None


def get_image_info(url_or_public_id):
    """
    Lấy thông tin chi tiết của ảnh từ Cloudinary
    """
    try:
        # Nếu là URL, extract public_id trước
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