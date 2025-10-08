import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import User, Product, Category, Banner, Blog, FAQ, Contact, Media, Project, Job
from app.models_rbac import Role, Permission
from app.forms import (LoginForm, CategoryForm, ProductForm, BannerForm,
                       BlogForm, FAQForm, UserForm, ProjectForm, JobForm,
                       RoleForm, PermissionForm)
from app.utils import save_upload_file, delete_file, get_albums, optimize_image
from app.decorators import permission_required, role_required
import shutil
import re
from html import unescape
from app.seo_config import MEDIA_KEYWORDS, KEYWORD_SCORES

# ==================== Giữ nguyên các hàm calculate_seo_score, calculate_blog_seo_score ====================
# (Copy từ file cũ - giữ nguyên 100%)

def calculate_seo_score(media):
    """Tính SEO score - dùng config từ seo_config.py"""
    score = 0
    issues = []
    recommendations = []
    checklist = []

    # 1. Alt Text (50 điểm)
    if media.alt_text:
        alt_len = len(media.alt_text)
        alt_lower = media.alt_text.lower()

        # 1.1. Độ dài (30 điểm)
        if 30 <= alt_len <= 125:
            score += 30
            checklist.append(('success', f'✓ Alt Text tối ưu ({alt_len} ký tự)'))
        elif 10 <= alt_len < 30:
            score += 15
            checklist.append(('warning', f'⚠ Alt Text hơi ngắn ({alt_len} ký tự)'))
        else:
            score += 5
            checklist.append(('danger', f'✗ Alt Text chưa tối ưu'))

        # 1.2. Keywords (20 điểm) - ĐỌC TỪ CONFIG
        has_primary = any(kw in alt_lower for kw in MEDIA_KEYWORDS['primary'])
        has_secondary = any(kw in alt_lower for kw in MEDIA_KEYWORDS['secondary'])
        has_brand = any(kw in alt_lower for kw in MEDIA_KEYWORDS['brand'])
        has_general = any(kw in alt_lower for kw in MEDIA_KEYWORDS['general'])

        if has_primary:
            score += KEYWORD_SCORES['primary']
            found_kw = next(kw for kw in MEDIA_KEYWORDS['primary'] if kw in alt_lower)
            checklist.append(('success', f'✓ Có keyword chính "{found_kw}"'))
        elif has_secondary and has_brand:
            score += KEYWORD_SCORES['secondary_brand']
            checklist.append(('success', '✓ Có keyword phụ + thương hiệu'))
        elif has_secondary:
            score += KEYWORD_SCORES['secondary']
            checklist.append(('info', 'ℹ Có keyword phụ (nên thêm thương hiệu)'))
            recommendations.append('Thêm "A.O Smith" để tăng điểm')
        elif has_brand:
            score += KEYWORD_SCORES['brand']
            checklist.append(('warning', '⚠ Chỉ có thương hiệu'))
            recommendations.append('Thêm keyword mô tả sản phẩm')
        elif has_general:
            score += KEYWORD_SCORES['general']
            checklist.append(('warning', '⚠ Chỉ có keyword chung'))
        else:
            checklist.append(('danger', '✗ Không có keywords'))
            recommendations.append(f'❗ Thêm: {", ".join(MEDIA_KEYWORDS["primary"][:2])}')
    else:
        issues.append('Thiếu Alt Text')
        checklist.append(('danger', '✗ Thiếu Alt Text'))

    # 2. Title (15 điểm)
    if media.title and len(media.title) > 0:
        title_len = len(media.title)
        if 20 <= title_len <= 100:
            score += 15
            checklist.append(('success', f'✓ Có Title tối ưu ({title_len} ký tự)'))
        elif title_len > 0:
            score += 10
            checklist.append(('info', f'ℹ Có Title nhưng độ dài chưa tối ưu ({title_len} ký tự)'))
    else:
        recommendations.append('Thêm Title attribute (hiện khi hover chuột)')
        checklist.append(('warning', '⚠ Nên thêm Title attribute'))

    # 3. Caption (15 điểm)
    if media.caption and len(media.caption) > 20:
        caption_len = len(media.caption)
        if caption_len >= 50:
            score += 15
            checklist.append(('success', f'✓ Có Caption mô tả chi tiết ({caption_len} ký tự)'))
        else:
            score += 10
            checklist.append(('info', f'ℹ Có Caption nhưng hơi ngắn ({caption_len} ký tự)'))
    else:
        recommendations.append('Thêm Caption để mô tả chi tiết hơn (tối thiểu 50 ký tự)')
        checklist.append(('warning', '⚠ Nên thêm Caption mô tả chi tiết'))

    # 4. Album Organization (10 điểm)
    if media.album:
        score += 10
        checklist.append(('success', f'✓ Đã phân loại vào Album "{media.album}"'))
    else:
        recommendations.append('Phân loại ảnh vào Album để quản lý tốt hơn')
        checklist.append(('warning', '⚠ Nên phân loại vào Album'))

    # 5. Image Size (10 điểm)
    if media.width and media.height:
        pixels = media.width * media.height
        if media.width <= 1920 and media.height <= 1200:
            score += 10
            checklist.append(('success', f'✓ Kích thước phù hợp ({media.width}×{media.height}px)'))
        elif media.width <= 2560 and media.height <= 1600:
            score += 7
            recommendations.append(f'Resize ảnh xuống ≤1920px để tối ưu tốc độ tải')
            checklist.append(('info', f'ℹ Ảnh hơi lớn ({media.width}×{media.height}px)'))
        else:
            score += 3
            issues.append('Ảnh có kích thước quá lớn')
            recommendations.append(f'❗ Resize ảnh về ≤1920×1200px (hiện tại: {media.width}×{media.height}px)')
            checklist.append(('danger', f'✗ Ảnh quá lớn ({media.width}×{media.height}px)'))

    # 6. File Size (10 điểm)
    if media.file_size:
        size_mb = media.file_size / (1024 * 1024)
        if size_mb <= 0.2:
            score += 10
            checklist.append(('success', f'✓ Dung lượng tối ưu ({size_mb:.2f} MB)'))
        elif size_mb <= 0.5:
            score += 8
            checklist.append(('success', f'✓ Dung lượng tốt ({size_mb:.2f} MB)'))
        elif size_mb <= 1.0:
            score += 5
            recommendations.append(f'Nén ảnh để giảm dung lượng xuống < 0.5MB (hiện tại: {size_mb:.2f} MB)')
            checklist.append(('info', f'ℹ Dung lượng chấp nhận được ({size_mb:.2f} MB)'))
        elif size_mb <= 2.0:
            score += 2
            issues.append('File hơi nặng')
            recommendations.append(f'❗ Nén ảnh xuống < 1MB (hiện tại: {size_mb:.2f} MB)')
            checklist.append(('warning', f'⚠ File hơi nặng ({size_mb:.2f} MB)'))
        else:
            issues.append('File quá nặng')
            recommendations.append(f'❗❗ Nén ảnh xuống < 1MB ngay! (hiện tại: {size_mb:.2f} MB)')
            checklist.append(('danger', f'✗ File quá nặng ({size_mb:.2f} MB)'))

    # Xác định grade
    if score >= 90:
        grade = 'A+'
        grade_text = 'Xuất sắc'
        grade_class = 'success'
    elif score >= 80:
        grade = 'A'
        grade_text = 'Rất tốt'
        grade_class = 'success'
    elif score >= 70:
        grade = 'B+'
        grade_text = 'Tốt'
        grade_class = 'info'
    elif score >= 60:
        grade = 'B'
        grade_text = 'Khá'
        grade_class = 'info'
    elif score >= 50:
        grade = 'C'
        grade_text = 'Trung bình'
        grade_class = 'warning'
    elif score >= 40:
        grade = 'D'
        grade_text = 'Yếu'
        grade_class = 'warning'
    else:
        grade = 'F'
        grade_text = 'Cần cải thiện gấp'
        grade_class = 'danger'

    return {
        'score': score,
        'grade': grade,
        'grade_text': grade_text,
        'grade_class': grade_class,
        'issues': issues,
        'recommendations': recommendations,
        'checklist': checklist
    }


def calculate_blog_seo_score(blog):
    """Tính toán điểm SEO cho blog post"""
    score = 0
    issues = []
    recommendations = []
    checklist = []

    # === 1. TITLE SEO (20 điểm) ===
    if blog.title:
        title_len = len(blog.title)
        title_lower = blog.title.lower()

        if 30 <= title_len <= 60:
            score += 10
            checklist.append(('success', f'✓ Tiêu đề tối ưu ({title_len} ký tự)'))
        elif 20 <= title_len < 30:
            score += 7
            checklist.append(('info', f'ℹ Tiêu đề hơi ngắn ({title_len}/30 ký tự)'))
            recommendations.append('Mở rộng tiêu đề lên 30-60 ký tự')
        elif 60 < title_len <= 70:
            score += 7
            checklist.append(('warning', f'⚠ Tiêu đề hơi dài ({title_len}/60 ký tự)'))
            recommendations.append('Rút gọn tiêu đề xuống 30-60 ký tự')
        else:
            score += 3
            issues.append('Tiêu đề quá ngắn hoặc quá dài')
            checklist.append(('danger', f'✗ Tiêu đề chưa tối ưu ({title_len} ký tự)'))
            recommendations.append('Tiêu đề nên 30-60 ký tự để hiển thị đầy đủ trên Google')

        if blog.focus_keyword and blog.focus_keyword.lower() in title_lower:
            score += 10
            checklist.append(('success', f'✓ Keyword "{blog.focus_keyword}" có trong tiêu đề'))
        elif blog.focus_keyword:
            recommendations.append(f'❗ Thêm keyword "{blog.focus_keyword}" vào tiêu đề')
            checklist.append(('danger', '✗ Keyword không có trong tiêu đề'))
    else:
        issues.append('Thiếu tiêu đề')
        checklist.append(('danger', '✗ Thiếu tiêu đề'))

    # === 2. META DESCRIPTION (15 điểm) ===
    if blog.meta_description:
        desc_len = len(blog.meta_description)
        desc_lower = blog.meta_description.lower()

        if 120 <= desc_len <= 160:
            score += 10
            checklist.append(('success', f'✓ Meta description tối ưu ({desc_len} ký tự)'))
        elif 100 <= desc_len < 120:
            score += 7
            checklist.append(('info', f'ℹ Meta description hơi ngắn ({desc_len}/120 ký tự)'))
        elif 160 < desc_len <= 180:
            score += 7
            checklist.append(('warning', f'⚠ Meta description hơi dài ({desc_len}/160 ký tự)'))
        else:
            score += 3
            issues.append('Meta description chưa tối ưu')
            checklist.append(('warning', f'⚠ Meta description: {desc_len} ký tự'))
            recommendations.append('Meta description nên 120-160 ký tự')

        if blog.focus_keyword and blog.focus_keyword.lower() in desc_lower:
            score += 5
            checklist.append(('success', '✓ Keyword có trong meta description'))
        elif blog.focus_keyword:
            recommendations.append('Thêm keyword vào meta description')
            checklist.append(('info', 'ℹ Nên thêm keyword vào meta description'))
    else:
        issues.append('Thiếu meta description')
        recommendations.append('❗ Thêm meta description 120-160 ký tự')
        checklist.append(('danger', '✗ Thiếu meta description'))

    # === 3. FOCUS KEYWORD ANALYSIS (25 điểm) ===
    if blog.focus_keyword:
        keyword = blog.focus_keyword.lower()
        content_text = ''
        if blog.content:
            content_text = re.sub(r'<[^>]+>', '', blog.content)
            content_text = unescape(content_text)

        content_lower = content_text.lower()

        if content_lower:
            keyword_count = content_lower.count(keyword)
            words = content_lower.split()
            word_count = len(words)
            density = (keyword_count / word_count * 100) if word_count > 0 else 0

            if 0.5 <= density <= 2.5:
                score += 10
                checklist.append(('success', f'✓ Mật độ keyword tối ưu: {density:.1f}% ({keyword_count} lần)'))
            elif 0.1 <= density < 0.5:
                score += 6
                checklist.append(('info', f'ℹ Mật độ keyword thấp: {density:.1f}% ({keyword_count} lần)'))
                recommendations.append(f'Sử dụng keyword "{keyword}" nhiều hơn (mật độ hiện tại: {density:.1f}%)')
            elif density > 2.5:
                score += 4
                checklist.append(('warning', f'⚠ Mật độ keyword cao: {density:.1f}% (nguy cơ spam)'))
                recommendations.append(f'Giảm mật độ keyword xuống 0.5-2.5% (hiện tại: {density:.1f}%)')
            else:
                issues.append('Keyword xuất hiện quá ít')
                checklist.append(('danger', f'✗ Keyword chỉ xuất hiện {keyword_count} lần'))
                recommendations.append(f'❗ Thêm keyword "{keyword}" vào nội dung (ít nhất 3-5 lần)')

        if content_lower:
            first_150_words = ' '.join(content_lower.split()[:150])
            if keyword in first_150_words:
                score += 8
                checklist.append(('success', '✓ Keyword có trong đoạn đầu (150 từ đầu)'))
            else:
                recommendations.append('❗ Thêm keyword vào đoạn đầu tiên')
                checklist.append(('danger', '✗ Keyword không có trong đoạn đầu'))

        if blog.content:
            headings = re.findall(r'<h[23][^>]*>(.*?)</h[23]>', blog.content.lower())
            has_keyword_in_heading = any(keyword in h for h in headings)

            if has_keyword_in_heading:
                score += 7
                checklist.append(('success', '✓ Keyword có trong tiêu đề phụ (H2/H3)'))
            elif headings:
                recommendations.append('Thêm keyword vào ít nhất 1 tiêu đề phụ (H2/H3)')
                checklist.append(('warning', '⚠ Keyword không có trong tiêu đề phụ'))
            else:
                recommendations.append('Thêm tiêu đề phụ (H2, H3) có chứa keyword')
                checklist.append(('danger', '✗ Chưa có tiêu đề phụ (H2/H3)'))
    else:
        issues.append('Chưa có focus keyword')
        recommendations.append('❗❗ Chọn focus keyword để tối ưu SEO')
        checklist.append(('danger', '✗ Chưa có focus keyword'))

    # === 4. CONTENT LENGTH (15 điểm) ===
    if blog.content:
        content_text = re.sub(r'<[^>]+>', '', blog.content)
        content_text = unescape(content_text)
        word_count = len(content_text.split())

        if word_count >= 1000:
            score += 15
            checklist.append(('success', f'✓ Nội dung dài và chi tiết ({word_count} từ)'))
        elif word_count >= 800:
            score += 13
            checklist.append(('success', f'✓ Nội dung đầy đủ ({word_count} từ)'))
        elif word_count >= 500:
            score += 10
            checklist.append(('info', f'ℹ Nội dung khá ({word_count} từ)'))
            recommendations.append('Mở rộng nội dung lên 800-1000 từ để SEO tốt hơn')
        elif word_count >= 300:
            score += 5
            checklist.append(('warning', f'⚠ Nội dung hơi ngắn ({word_count} từ)'))
            recommendations.append('❗ Nội dung nên ít nhất 500-800 từ')
        else:
            issues.append('Nội dung quá ngắn')
            checklist.append(('danger', f'✗ Nội dung quá ngắn ({word_count} từ)'))
            recommendations.append('❗❗ Viết thêm nội dung (tối thiểu 500 từ)')
    else:
        issues.append('Chưa có nội dung')
        checklist.append(('danger', '✗ Chưa có nội dung'))

    # === 5. IMAGE SEO (10 điểm) ===
    if blog.image:
        media_info = blog.get_media_seo_info()
        if media_info and media_info.get('alt_text'):
            alt_text = media_info['alt_text']
            if blog.focus_keyword and blog.focus_keyword.lower() in alt_text.lower():
                score += 10
                checklist.append(('success', '✓ Ảnh có Alt Text chứa keyword'))
            else:
                score += 7
                checklist.append(('info', 'ℹ Ảnh có Alt Text nhưng không có keyword'))
                if blog.focus_keyword:
                    recommendations.append(f'Thêm keyword "{blog.focus_keyword}" vào Alt Text của ảnh')
        else:
            score += 3
            recommendations.append('❗ Thêm Alt Text cho ảnh đại diện')
            checklist.append(('warning', '⚠ Ảnh thiếu Alt Text'))
    else:
        recommendations.append('Thêm ảnh đại diện cho bài viết')
        checklist.append(('warning', '⚠ Chưa có ảnh đại diện'))

    # === 6. INTERNAL LINKS (10 điểm) ===
    if blog.content:
        internal_links = len(re.findall(r'href=["\'](?:/|(?:https?://)?(?:www\.)?aosmith\.com\.vn)', blog.content))
        if internal_links >= 3:
            score += 10
            checklist.append(('success', f'✓ Có {internal_links} liên kết nội bộ'))
        elif internal_links >= 2:
            score += 7
            checklist.append(('info', f'ℹ Có {internal_links} liên kết nội bộ (nên >= 3)'))
            recommendations.append('Thêm 1-2 liên kết nội bộ nữa')
        elif internal_links == 1:
            score += 4
            checklist.append(('warning', '⚠ Chỉ có 1 liên kết nội bộ'))
            recommendations.append('❗ Thêm ít nhất 2-3 liên kết đến bài viết/sản phẩm khác')
        else:
            recommendations.append('❗❗ Thêm 2-3 liên kết nội bộ (link đến bài viết/sản phẩm liên quan)')
            checklist.append(('danger', '✗ Chưa có liên kết nội bộ'))

    # === 7. READABILITY & STRUCTURE (5 điểm) ===
    if blog.content:
        paragraphs = len(re.findall(r'<p[^>]*>.*?</p>', blog.content))
        headings = len(re.findall(r'<h[2-6][^>]*>.*?</h[2-6]>', blog.content))

        structure_score = 0
        if headings >= 3:
            structure_score += 3
            checklist.append(('success', f'✓ Có {headings} tiêu đề phụ (H2-H6)'))
        elif headings >= 1:
            structure_score += 2
            recommendations.append('Thêm tiêu đề phụ (H2, H3) để cải thiện cấu trúc')
            checklist.append(('info', f'ℹ Có {headings} tiêu đề phụ (nên >= 3)'))
        else:
            recommendations.append('❗ Thêm tiêu đề phụ (H2, H3) để chia nhỏ nội dung')
            checklist.append(('warning', '⚠ Chưa có tiêu đề phụ'))

        if paragraphs >= 5:
            structure_score += 2
            checklist.append(('success', f'✓ Nội dung được chia {paragraphs} đoạn'))
        elif paragraphs >= 3:
            structure_score += 1
            checklist.append(('info', f'ℹ Có {paragraphs} đoạn văn'))

        score += structure_score

    # === GRADE CALCULATION ===
    if score >= 90:
        grade, grade_text, grade_class = 'A+', 'Xuất sắc', 'success'
    elif score >= 85:
        grade, grade_text, grade_class = 'A', 'Rất tốt', 'success'
    elif score >= 75:
        grade, grade_text, grade_class = 'B+', 'Tốt', 'info'
    elif score >= 65:
        grade, grade_text, grade_class = 'B', 'Khá', 'info'
    elif score >= 55:
        grade, grade_text, grade_class = 'C', 'Trung bình', 'warning'
    elif score >= 45:
        grade, grade_text, grade_class = 'D', 'Yếu', 'warning'
    else:
        grade, grade_text, grade_class = 'F', 'Cần cải thiện gấp', 'danger'

    return {
        'score': score,
        'grade': grade,
        'grade_text': grade_text,
        'grade_class': grade_class,
        'issues': issues,
        'recommendations': recommendations,
        'checklist': checklist
    }


# Tạo Blueprint cho admin
admin_bp = Blueprint('admin', __name__)


# ==================== Helper function ====================
def get_image_from_form(form_image_field, field_name='image', folder='uploads'):
    """Lấy đường dẫn ảnh từ form - Ưu tiên selected_image từ media picker"""
    from werkzeug.datastructures import FileStorage

    selected_image = request.form.get('selected_image_path')
    if selected_image and selected_image.strip():
        path = selected_image.strip()
        if path.startswith('http://') or path.startswith('https://'):
            return path
        if not path.startswith('/'):
            path = '/' + path
        if not path.startswith('/static/'):
            if path.startswith('/uploads/'):
                path = '/static' + path
            else:
                path = '/static/' + path.lstrip('/')
        return path

    if form_image_field and form_image_field.data:
        if isinstance(form_image_field.data, FileStorage):
            result = save_upload_file(form_image_field.data, folder=folder, optimize=True)
            if result and isinstance(result, tuple):
                filepath = result[0]
                return filepath
            return result
        elif isinstance(form_image_field.data, str):
            return form_image_field.data

    return None


# ==================== LOGIN & LOGOUT ====================
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Trang đăng nhập admin - KHÔNG CẦN QUYỀN"""
    if current_user.is_authenticated:
        # Redirect dựa vào role
        if current_user.has_any_permission('manage_users', 'manage_products', 'manage_categories'):
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('admin.welcome'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')

            if next_page:
                return redirect(next_page)

            # Redirect dựa vào role
            if user.has_any_permission('manage_users', 'manage_products', 'manage_categories'):
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('admin.welcome'))
        else:
            flash('Email hoặc mật khẩu không đúng!', 'danger')

    return render_template('admin/login.html', form=form)


@admin_bp.route('/logout')
@login_required
def logout():
    """Đăng xuất - KHÔNG CẦN QUYỀN ĐẶC BIỆT"""
    logout_user()
    flash('Đã đăng xuất thành công!', 'success')
    return redirect(url_for('admin.login'))


# ==================== DASHBOARD ====================
@admin_bp.route('/dashboard')
@permission_required('view_dashboard')
def dashboard():
    """
    Dashboard đầy đủ - CHỈ cho Admin & Editor
    User khác redirect sang Welcome
    """
    # Kiểm tra quyền - chỉ Admin/Editor vào được
    if not current_user.has_any_permission('manage_users', 'manage_products', 'manage_categories'):
        return redirect(url_for('admin.welcome'))

    # Dashboard cho Admin/Editor
    total_products = Product.query.count()
    total_categories = Category.query.count()
    total_blogs = Blog.query.count()
    total_contacts = Contact.query.filter_by(is_read=False).count()
    recent_products = Product.query.order_by(Product.created_at.desc()).limit(5).all()
    recent_contacts = Contact.query.order_by(Contact.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_products=total_products,
                           total_categories=total_categories,
                           total_blogs=total_blogs,
                           total_contacts=total_contacts,
                           recent_products=recent_products,
                           recent_contacts=recent_contacts)

# ==================== WELCOME USER ====================
@admin_bp.route('/welcome')
@login_required
def welcome():
    """Trang chào mừng cho User thường (không phải Admin/Editor)"""
    # Nếu là Admin/Editor, redirect về dashboard
    if current_user.has_any_permission('manage_users', 'manage_products', 'manage_categories'):
        return redirect(url_for('admin.dashboard'))

    # Lấy số liên hệ chưa đọc (nếu có quyền xem)
    total_contacts = 0
    if current_user.has_any_permission('view_contacts', 'manage_contacts'):
        total_contacts = Contact.query.filter_by(is_read=False).count()

    return render_template('admin/welcome.html', total_contacts=total_contacts)


# ==================== QUẢN LÝ DANH MỤC ====================
@admin_bp.route('/categories')
@permission_required('manage_categories')  # ✅ Quản lý danh mục
def categories():
    """Danh sách danh mục"""
    page = request.args.get('page', 1, type=int)
    categories = Category.query.order_by(Category.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/categories.html', categories=categories)


@admin_bp.route('/categories/add', methods=['GET', 'POST'])
@permission_required('manage_categories')  # ✅ Quản lý danh mục
def add_category():
    """Thêm danh mục mới"""
    form = CategoryForm()

    if form.validate_on_submit():
        image_path = None
        if form.image.data:
            result = save_upload_file(form.image.data, folder='categories')
            image_path = result[0] if isinstance(result, tuple) else result

        category = Category(
            name=form.name.data,
            slug=form.slug.data,
            description=form.description.data,
            image=image_path,
            is_active=form.is_active.data
        )

        db.session.add(category)
        db.session.commit()

        flash('Đã thêm danh mục thành công!', 'success')
        return redirect(url_for('admin.categories'))

    return render_template('admin/category_form.html', form=form, title='Thêm danh mục')


@admin_bp.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
@permission_required('manage_categories')  # ✅ Quản lý danh mục
def edit_category(id):
    """Sửa danh mục"""
    category = Category.query.get_or_404(id)
    form = CategoryForm(obj=category)

    if form.validate_on_submit():
        if form.image.data:
            result = save_upload_file(form.image.data, folder='categories')
            image_path = result[0] if isinstance(result, tuple) else result
            category.image = image_path

        category.name = form.name.data
        category.slug = form.slug.data
        category.description = form.description.data
        category.is_active = form.is_active.data

        db.session.commit()

        flash('Đã cập nhật danh mục thành công!', 'success')
        return redirect(url_for('admin.categories'))

    return render_template('admin/category_form.html', form=form, title='Sửa danh mục')


@admin_bp.route('/categories/delete/<int:id>')
@permission_required('manage_categories')  # ✅ Quản lý danh mục
def delete_category(id):
    """Xóa danh mục"""
    category = Category.query.get_or_404(id)

    if category.products.count() > 0:
        flash('Không thể xóa danh mục đang có sản phẩm!', 'danger')
        return redirect(url_for('admin.categories'))

    db.session.delete(category)
    db.session.commit()

    flash('Đã xóa danh mục thành công!', 'success')
    return redirect(url_for('admin.categories'))


# ==================== QUẢN LÝ SẢN PHẨM ====================
@admin_bp.route('/products')
@permission_required('view_products')  # ✅ Xem sản phẩm
def products():
    """Danh sách sản phẩm"""
    page = request.args.get('page', 1, type=int)
    products = Product.query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/products.html', products=products)


@admin_bp.route('/products/add', methods=['GET', 'POST'])
@permission_required('manage_products')  # ✅ Quản lý sản phẩm
def add_product():
    """Thêm sản phẩm mới"""
    form = ProductForm()

    if form.validate_on_submit():
        image_path = get_image_from_form(form.image, 'image', folder='products')

        product = Product(
            name=form.name.data,
            slug=form.slug.data,
            description=form.description.data,
            price=form.price.data,
            old_price=form.old_price.data,
            category_id=form.category_id.data,
            image=image_path,
            is_featured=form.is_featured.data,
            is_active=form.is_active.data
        )

        db.session.add(product)
        db.session.commit()

        flash('Đã thêm sản phẩm thành công!', 'success')
        return redirect(url_for('admin.products'))

    return render_template('admin/product_form.html', form=form, title='Thêm sản phẩm')


@admin_bp.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@permission_required('manage_products')  # ✅ Quản lý sản phẩm
def edit_product(id):
    """Sửa sản phẩm"""
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)

    if form.validate_on_submit():
        new_image = get_image_from_form(form.image, 'image', folder='products')
        if new_image:
            product.image = new_image

        product.name = form.name.data
        product.slug = form.slug.data
        product.description = form.description.data
        product.price = form.price.data
        product.old_price = form.old_price.data
        product.category_id = form.category_id.data
        product.is_featured = form.is_featured.data
        product.is_active = form.is_active.data

        db.session.commit()

        flash('Đã cập nhật sản phẩm thành công!', 'success')
        return redirect(url_for('admin.products'))

    return render_template('admin/product_form.html', form=form, title='Sửa sản phẩm')


@admin_bp.route('/products/delete/<int:id>')
@permission_required('manage_products')  # ✅ Quản lý sản phẩm
def delete_product(id):
    """Xóa sản phẩm"""
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()

    flash('Đã xóa sản phẩm thành công!', 'success')
    return redirect(url_for('admin.products'))


# ==================== QUẢN LÝ BANNER ====================
@admin_bp.route('/banners')
@permission_required('manage_banners')  # ✅ Quản lý banners
def banners():
    """Danh sách banner"""
    banners = Banner.query.order_by(Banner.order).all()
    return render_template('admin/banners.html', banners=banners)


@admin_bp.route('/banners/add', methods=['GET', 'POST'])
@permission_required('manage_banners')  # ✅ Quản lý banners
def add_banner():
    """Thêm banner mới"""
    form = BannerForm()

    if form.validate_on_submit():
        image_path = get_image_from_form(form.image, 'image', folder='banners')

        if not image_path:
            flash('Vui lòng chọn hoặc upload ảnh banner!', 'danger')
            return render_template('admin/banner_form.html', form=form, title='Thêm banner')

        banner = Banner(
            title=form.title.data,
            subtitle=form.subtitle.data,
            image=image_path,
            link=form.link.data,
            button_text=form.button_text.data,
            order=form.order.data or 0,
            is_active=form.is_active.data
        )

        db.session.add(banner)
        db.session.commit()

        flash('Đã thêm banner thành công!', 'success')
        return redirect(url_for('admin.banners'))

    return render_template('admin/banner_form.html', form=form, title='Thêm banner')


@admin_bp.route('/banners/edit/<int:id>', methods=['GET', 'POST'])
@permission_required('manage_banners')  # ✅ Quản lý banners
def edit_banner(id):
    """Sửa banner"""
    banner = Banner.query.get_or_404(id)
    form = BannerForm(obj=banner)

    if form.validate_on_submit():
        new_image = get_image_from_form(form.image, 'image', folder='banners')
        if new_image:
            banner.image = new_image

        banner.title = form.title.data
        banner.subtitle = form.subtitle.data
        banner.link = form.link.data
        banner.button_text = form.button_text.data
        banner.order = form.order.data or 0
        banner.is_active = form.is_active.data

        db.session.commit()

        flash('Đã cập nhật banner thành công!', 'success')
        return redirect(url_for('admin.banners'))

    return render_template('admin/banner_form.html', form=form, title='Sửa banner')


@admin_bp.route('/banners/delete/<int:id>')
@permission_required('manage_banners')  # ✅ Quản lý banners
def delete_banner(id):
    """Xóa banner"""
    banner = Banner.query.get_or_404(id)
    db.session.delete(banner)
    db.session.commit()

    flash('Đã xóa banner thành công!', 'success')
    return redirect(url_for('admin.banners'))


# ==================== QUẢN LÝ BLOG ====================
@admin_bp.route('/blogs')
@permission_required('view_blogs')  # ✅ Xem blog
def blogs():
    """Danh sách blog"""
    page = request.args.get('page', 1, type=int)
    blogs = Blog.query.order_by(Blog.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/blogs.html', blogs=blogs)


@admin_bp.route('/blogs/add', methods=['GET', 'POST'])
@permission_required('create_blog')  # ✅ Tạo blog
def add_blog():
    """Thêm blog mới với SEO optimization"""
    form = BlogForm()

    if form.validate_on_submit():
        image_path = get_image_from_form(form.image, 'image', folder='blogs')

        blog = Blog(
            title=form.title.data,
            slug=form.slug.data,
            excerpt=form.excerpt.data,
            content=form.content.data,
            image=image_path,
            author=form.author.data or current_user.username,
            is_featured=form.is_featured.data,
            is_active=form.is_active.data,
            focus_keyword=form.focus_keyword.data,
            meta_title=form.meta_title.data or form.title.data,
            meta_description=form.meta_description.data or form.excerpt.data,
            meta_keywords=form.meta_keywords.data
        )

        blog.calculate_reading_time()
        blog.update_seo_score()

        db.session.add(blog)
        db.session.commit()

        seo_result = blog.get_seo_info()
        flash(f'✓ Đã thêm bài viết! Điểm SEO: {seo_result["score"]}/100 ({seo_result["grade"]})', 'success')

        return redirect(url_for('admin.blogs'))

    return render_template('admin/blog_form.html', form=form, title='Thêm bài viết')


@admin_bp.route('/blogs/edit/<int:id>', methods=['GET', 'POST'])
@permission_required('edit_all_blogs')  # ✅ Sửa tất cả blog
def edit_blog(id):
    """Sửa blog với SEO optimization"""
    blog = Blog.query.get_or_404(id)
    form = BlogForm(obj=blog)

    if form.validate_on_submit():
        new_image = get_image_from_form(form.image, 'image', folder='blogs')
        if new_image:
            blog.image = new_image

        blog.title = form.title.data
        blog.slug = form.slug.data
        blog.excerpt = form.excerpt.data
        blog.content = form.content.data
        blog.author = form.author.data
        blog.is_featured = form.is_featured.data
        blog.is_active = form.is_active.data
        blog.focus_keyword = form.focus_keyword.data
        blog.meta_title = form.meta_title.data or form.title.data
        blog.meta_description = form.meta_description.data or form.excerpt.data
        blog.meta_keywords = form.meta_keywords.data

        blog.calculate_reading_time()
        blog.update_seo_score()

        db.session.commit()

        seo_result = blog.get_seo_info()
        flash(f'✓ Đã cập nhật bài viết! Điểm SEO: {seo_result["score"]}/100 ({seo_result["grade"]})', 'success')

        return redirect(url_for('admin.blogs'))

    return render_template('admin/blog_form.html', form=form, title='Sửa bài viết', blog=blog)


@admin_bp.route('/api/check-blog-seo', methods=['POST'])
@permission_required('view_blogs')  # ✅ Xem blog
def api_check_blog_seo():
    """API để check SEO score real-time khi đang viết bài"""
    data = request.get_json()

    temp_blog = Blog(
        title=data.get('title', ''),
        content=data.get('content', ''),
        focus_keyword=data.get('focus_keyword', ''),
        meta_title=data.get('meta_title', ''),
        meta_description=data.get('meta_description', ''),
        image=data.get('image', '')
    )

    seo_result = calculate_blog_seo_score(temp_blog)
    return jsonify(seo_result)


@admin_bp.route('/blogs/delete/<int:id>')
@permission_required('delete_blog')  # ✅ Xóa blog
def delete_blog(id):
    """Xóa blog"""
    blog = Blog.query.get_or_404(id)
    db.session.delete(blog)
    db.session.commit()

    flash('Đã xóa bài viết thành công!', 'success')
    return redirect(url_for('admin.blogs'))


# ==================== QUẢN LÝ FAQ ====================
@admin_bp.route('/faqs')
@permission_required('manage_faqs')  # ✅ Quản lý FAQs
def faqs():
    """Danh sách FAQ"""
    faqs = FAQ.query.order_by(FAQ.order).all()
    return render_template('admin/faqs.html', faqs=faqs)


@admin_bp.route('/faqs/add', methods=['GET', 'POST'])
@permission_required('manage_faqs')  # ✅ Quản lý FAQs
def add_faq():
    """Thêm FAQ mới"""
    form = FAQForm()

    if form.validate_on_submit():
        faq = FAQ(
            question=form.question.data,
            answer=form.answer.data,
            order=form.order.data or 0,
            is_active=form.is_active.data
        )

        db.session.add(faq)
        db.session.commit()

        flash('Đã thêm FAQ thành công!', 'success')
        return redirect(url_for('admin.faqs'))

    return render_template('admin/faq_form.html', form=form, title='Thêm FAQ')


@admin_bp.route('/faqs/edit/<int:id>', methods=['GET', 'POST'])
@permission_required('manage_faqs')  # ✅ Quản lý FAQs
def edit_faq(id):
    """Sửa FAQ"""
    faq = FAQ.query.get_or_404(id)
    form = FAQForm(obj=faq)

    if form.validate_on_submit():
        faq.question = form.question.data
        faq.answer = form.answer.data
        faq.order = form.order.data or 0
        faq.is_active = form.is_active.data

        db.session.commit()

        flash('Đã cập nhật FAQ thành công!', 'success')
        return redirect(url_for('admin.faqs'))

    return render_template('admin/faq_form.html', form=form, title='Sửa FAQ')


@admin_bp.route('/faqs/delete/<int:id>')
@permission_required('manage_faqs')  # ✅ Quản lý FAQs
def delete_faq(id):
    """Xóa FAQ"""
    faq = FAQ.query.get_or_404(id)
    db.session.delete(faq)
    db.session.commit()

    flash('Đã xóa FAQ thành công!', 'success')
    return redirect(url_for('admin.faqs'))


# ==================== QUẢN LÝ NGƯỜI DÙNG ====================
@admin_bp.route('/users')
@permission_required('view_users')  # ✅ Xem danh sách user
def users():
    """Danh sách người dùng với filter theo role"""
    role_filter = request.args.get('role', '')

    query = User.query
    if role_filter:
        role_obj = Role.query.filter_by(name=role_filter).first()
        if role_obj:
            query = query.filter_by(role_id=role_obj.id)

    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/add', methods=['GET', 'POST'])
@permission_required('manage_users')  # ✅ Quản lý users
def add_user():
    """Thêm người dùng mới"""
    form = UserForm()

    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role_id=form.role_id.data
        )

        if form.password.data:
            user.set_password(form.password.data)
        else:
            flash('Vui lòng nhập mật khẩu!', 'danger')
            return render_template('admin/user_form.html', form=form, title='Thêm người dùng')

        db.session.add(user)
        db.session.commit()

        flash(f'Đã thêm người dùng "{user.username}" với vai trò "{user.role_display_name}"!', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', form=form, title='Thêm người dùng')


@admin_bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@permission_required('manage_users')  # ✅ Quản lý users
def edit_user(id):
    """Sửa người dùng"""
    user = User.query.get_or_404(id)
    form = UserForm(user=user, obj=user)

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role_id = form.role_id.data

        if form.password.data:
            user.set_password(form.password.data)

        db.session.commit()

        flash(f'Đã cập nhật người dùng "{user.username}"!', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', form=form, title='Sửa người dùng')


@admin_bp.route('/users/delete/<int:id>')
@permission_required('manage_users')  # ✅ Quản lý users
def delete_user(id):
    """Xóa người dùng"""
    if id == current_user.id:
        flash('Không thể xóa tài khoản của chính mình!', 'danger')
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()

    flash('Đã xóa người dùng thành công!', 'success')
    return redirect(url_for('admin.users'))


# ==================== QUẢN LÝ LIÊN HỆ ====================
@admin_bp.route('/contacts')
@permission_required('view_contacts')  # ✅ Xem liên hệ
def contacts():
    """Danh sách liên hệ"""
    page = request.args.get('page', 1, type=int)
    contacts = Contact.query.order_by(Contact.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/contacts.html', contacts=contacts)


@admin_bp.route('/contacts/view/<int:id>')
@permission_required('view_contacts')  # ✅ Xem liên hệ
def view_contact(id):
    """Xem chi tiết liên hệ"""
    contact = Contact.query.get_or_404(id)

    if not contact.is_read:
        contact.is_read = True
        db.session.commit()

    return render_template('admin/contact_detail.html', contact=contact)


@admin_bp.route('/contacts/delete/<int:id>')
@permission_required('manage_contacts')  # ✅ Quản lý liên hệ
def delete_contact(id):
    """Xóa liên hệ"""
    contact = Contact.query.get_or_404(id)
    db.session.delete(contact)
    db.session.commit()

    flash('Đã xóa liên hệ thành công!', 'success')
    return redirect(url_for('admin.contacts'))


# ==================== QUẢN LÝ MEDIA LIBRARY ====================
@admin_bp.route('/media')
@permission_required('view_media')  # ✅ Xem thư viện media
def media():
    """Trang quản lý Media Library với SEO status"""
    page = request.args.get('page', 1, type=int)
    album_filter = request.args.get('album', '')
    seo_filter = request.args.get('seo', '')

    query = Media.query
    if album_filter:
        query = query.filter_by(album=album_filter)

    media_files = query.order_by(Media.created_at.desc()).paginate(
        page=page, per_page=24, error_out=False
    )

    media_with_seo = []
    for m in media_files.items:
        seo_result = calculate_seo_score(m)
        media_with_seo.append({
            'media': m,
            'seo': seo_result
        })

    if seo_filter:
        if seo_filter == 'excellent':
            media_with_seo = [m for m in media_with_seo if m['seo']['score'] >= 85]
        elif seo_filter == 'good':
            media_with_seo = [m for m in media_with_seo if 65 <= m['seo']['score'] < 85]
        elif seo_filter == 'fair':
            media_with_seo = [m for m in media_with_seo if 50 <= m['seo']['score'] < 65]
        elif seo_filter == 'poor':
            media_with_seo = [m for m in media_with_seo if m['seo']['score'] < 50]

    albums = get_albums()
    total_files = Media.query.count()
    total_size = db.session.query(db.func.sum(Media.file_size)).scalar() or 0
    total_size_mb = round(total_size / (1024 * 1024), 2)

    all_media = Media.query.all()
    seo_stats = {
        'excellent': sum(1 for m in all_media if calculate_seo_score(m)['score'] >= 85),
        'good': sum(1 for m in all_media if 65 <= calculate_seo_score(m)['score'] < 85),
        'fair': sum(1 for m in all_media if 50 <= calculate_seo_score(m)['score'] < 65),
        'poor': sum(1 for m in all_media if calculate_seo_score(m)['score'] < 50),
    }

    return render_template(
        'admin/media.html',
        media_files=media_files,
        media_with_seo=media_with_seo,
        albums=albums,
        total_files=total_files,
        total_size_mb=total_size_mb,
        current_album=album_filter,
        seo_stats=seo_stats,
        current_seo_filter=seo_filter
    )


@admin_bp.route('/media/upload', methods=['GET', 'POST'])
@permission_required('upload_media')  # ✅ Upload media
def upload_media():
    """Upload media files với SEO optimization"""
    if request.method == 'POST':
        files = request.files.getlist('files')
        album = request.form.get('album', '').strip()
        folder = request.form.get('folder', 'general')
        default_alt_text = request.form.get('default_alt_text', '').strip()
        auto_alt_text = request.form.get('auto_alt_text') == 'on'

        if not files or not files[0].filename:
            flash('Vui lòng chọn file để upload!', 'warning')
            return redirect(url_for('admin.upload_media'))

        uploaded_count = 0
        errors = []

        for file in files:
            if file and file.filename:
                try:
                    if default_alt_text:
                        file_alt_text = default_alt_text
                    elif auto_alt_text:
                        from app.utils import slugify
                        name_without_ext = os.path.splitext(file.filename)[0]
                        file_alt_text = name_without_ext.replace('-', ' ').replace('_', ' ').title()
                    else:
                        file_alt_text = None

                    filepath, file_info = save_upload_file(
                        file,
                        folder=folder,
                        album=album if album else None,
                        alt_text=file_alt_text,
                        optimize=True
                    )

                    if filepath:
                        media = Media(
                            filename=file_info['filename'],
                            original_filename=file_info['original_filename'],
                            filepath=file_info['filepath'],
                            file_type=file_info['file_type'],
                            file_size=file_info['file_size'],
                            width=file_info['width'],
                            height=file_info['height'],
                            album=album if album else None,
                            alt_text=file_alt_text,
                            title=file_alt_text,
                            uploaded_by=current_user.id
                        )
                        db.session.add(media)
                        uploaded_count += 1
                    else:
                        errors.append(f"Không thể upload {file.filename}")

                except Exception as e:
                    errors.append(f"Lỗi upload {file.filename}: {str(e)}")

        if uploaded_count > 0:
            db.session.commit()
            flash(f'Đã upload thành công {uploaded_count} file!', 'success')

        if errors:
            for error in errors:
                flash(error, 'danger')

        return redirect(url_for('admin.media'))

    albums = get_albums()
    return render_template('admin/upload_media.html', albums=albums)


@admin_bp.route('/media/create-album', methods=['POST'])
@permission_required('manage_albums')  # ✅ Quản lý albums
def create_album():
    """Tạo album mới"""
    album_name = request.form.get('album_name', '').strip()

    if not album_name:
        flash('Vui lòng nhập tên album!', 'warning')
        return redirect(url_for('admin.media'))

    album_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'],
        'albums',
        secure_filename(album_name)
    )

    try:
        os.makedirs(album_path, exist_ok=True)
        flash(f'Đã tạo album "{album_name}" thành công!', 'success')
    except Exception as e:
        flash(f'Lỗi tạo album: {str(e)}', 'danger')

    return redirect(url_for('admin.media'))


@admin_bp.route('/media/delete/<int:id>')
@permission_required('delete_media')  # ✅ Xóa media
def delete_media(id):
    """Xóa media file (Cloudinary + local + DB)"""
    from app.utils import delete_file
    import logging

    logging.basicConfig(level=logging.INFO)
    def safe_print(*args):
        try:
            print(*args)
        except Exception:
            pass

    media = Media.query.get_or_404(id)
    album_name = media.album

    try:
        if media.filepath and "res.cloudinary.com" in media.filepath:
            safe_print(f"[Delete Cloudinary Start]: {repr(media.filepath)}")
            res = delete_file(media.filepath)
            safe_print(f"[Delete Cloudinary Result]: {res}")
        else:
            safe_print("[Delete Cloudinary]: Bỏ qua (không phải URL Cloudinary)")

        if media.filepath and media.filepath.startswith('/static/'):
            file_path = media.filepath.replace('/static/', '')
            full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], '..', file_path)
            abs_path = os.path.abspath(full_path)

            if os.path.exists(abs_path):
                os.remove(abs_path)
                safe_print(f"[Delete Local]: Đã xóa {abs_path}")
            else:
                safe_print(f"[Delete Local]: Không tìm thấy {abs_path}")

    except Exception as e:
        safe_print(f"[Delete Error]: {e}")
        logging.exception(e)

    try:
        db.session.delete(media)
        db.session.commit()
        flash('🗑️ Đã xóa ảnh khỏi hệ thống', 'success')
        safe_print("[DB Delete]: Media record removed successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xóa khỏi cơ sở dữ liệu: {e}', 'danger')
        safe_print(f"[DB Delete Error]: {e}")
        logging.exception(e)

    if album_name:
        return redirect(url_for('admin.media', album=album_name))
    return redirect(url_for('admin.media'))


@admin_bp.route('/media/delete-album/<album_name>')
@permission_required('manage_albums')  # ✅ Quản lý albums
def delete_album(album_name):
    """Xóa album (chỉ khi rỗng)"""
    remaining_files = Media.query.filter_by(album=album_name).count()

    if remaining_files > 0:
        flash(f'Không thể xóa album có {remaining_files} file! Vui lòng xóa hết file trước.', 'danger')
        return redirect(url_for('admin.media'))

    album_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'],
        'albums',
        secure_filename(album_name)
    )

    try:
        if os.path.exists(album_path):
            shutil.rmtree(album_path)
        flash(f'Đã xóa album "{album_name}" thành công!', 'success')
    except Exception as e:
        flash(f'Lỗi khi xóa album "{album_name}": {str(e)}', 'danger')

    return redirect(url_for('admin.media'))


@admin_bp.route('/media/edit/<int:id>', methods=['GET', 'POST'])
@permission_required('edit_media')  # ✅ Chỉnh sửa media
def edit_media(id):
    """Sửa thông tin media với SEO fields và hiển thị điểm SEO"""
    from app.forms import MediaSEOForm

    media = Media.query.get_or_404(id)
    form = MediaSEOForm(obj=media)

    if form.validate_on_submit():
        media.alt_text = form.alt_text.data.strip()
        media.title = form.title.data.strip() if form.title.data else None
        media.caption = form.caption.data.strip() if form.caption.data else None
        media.album = form.album.data.strip() if form.album.data else None

        if not media.alt_text:
            flash('Alt Text là bắt buộc cho SEO!', 'warning')
            albums = get_albums()
            seo_result = calculate_seo_score(media)
            return render_template('admin/edit_media.html',
                                   media=media,
                                   form=form,
                                   albums=albums,
                                   seo_result=seo_result)

        if len(media.alt_text) < 10:
            flash('Alt Text quá ngắn! Nên từ 30-125 ký tự.', 'warning')

        if not media.title:
            media.title = media.alt_text

        try:
            db.session.commit()

            seo_result = calculate_seo_score(media)
            flash(f'✓ Đã cập nhật thông tin media! Điểm SEO: {seo_result["score"]}/100 ({seo_result["grade"]})',
                  'success')

            if media.album:
                return redirect(url_for('admin.media', album=media.album))
            return redirect(url_for('admin.media'))

        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi lưu: {str(e)}', 'danger')

    albums = get_albums()
    seo_result = calculate_seo_score(media)

    return render_template('admin/edit_media.html',
                           media=media,
                           form=form,
                           albums=albums,
                           seo_result=seo_result)


@admin_bp.route('/media/bulk-edit', methods=['POST'])
@permission_required('edit_media')  # ✅ Chỉnh sửa media
def bulk_edit_media():
    """Bulk edit SEO cho nhiều media"""
    media_ids = request.form.getlist('media_ids[]')
    action = request.form.get('action')

    if not media_ids:
        return jsonify({'success': False, 'message': 'Chưa chọn file nào'})

    if action == 'set_alt_text':
        alt_text_template = request.form.get('alt_text_template', '')
        updated = 0

        for media_id in media_ids:
            media = Media.query.get(media_id)
            if media:
                alt_text = alt_text_template.replace('{filename}', media.original_filename)
                if media.album:
                    alt_text = alt_text.replace('{album}', media.album)

                media.alt_text = alt_text
                updated += 1

        db.session.commit()
        return jsonify({'success': True, 'message': f'Đã cập nhật {updated} file'})

    elif action == 'set_album':
        album_name = request.form.get('album_name', '')
        updated = Media.query.filter(Media.id.in_(media_ids)).update(
            {Media.album: album_name},
            synchronize_session=False
        )
        db.session.commit()
        return jsonify({'success': True, 'message': f'Đã chuyển {updated} file vào album "{album_name}"'})

    return jsonify({'success': False, 'message': 'Action không hợp lệ'})


@admin_bp.route('/media/check-seo/<int:id>')
@permission_required('view_media')  # ✅ Xem thư viện media
def check_media_seo(id):
    """API check SEO score của media - trả về JSON"""
    media = Media.query.get_or_404(id)
    seo_result = calculate_seo_score(media)
    return jsonify(seo_result)


# ==================== API CHO MEDIA PICKER ====================
@admin_bp.route('/api/media')
@permission_required('view_media')  # ✅ Xem thư viện media
def api_media():
    """API trả về danh sách media với đường dẫn chuẩn hóa"""
    album = request.args.get('album', '')
    search = request.args.get('search', '')

    query = Media.query
    if album:
        query = query.filter_by(album=album)
    if search:
        query = query.filter(Media.original_filename.ilike(f'%{search}%'))

    media_list = query.order_by(Media.created_at.desc()).limit(100).all()

    albums_data = get_albums()
    album_names = [a['name'] if isinstance(a, dict) else a for a in albums_data]

    def normalize_filepath(media):
        """Chuẩn hóa filepath để đảm bảo có thể hiển thị được"""
        filepath = media.filepath

        if not filepath:
            return ''

        if filepath.startswith('http://') or filepath.startswith('https://'):
            return filepath

        if not filepath.startswith('/'):
            filepath = '/' + filepath

        if not filepath.startswith('/static/'):
            if filepath.startswith('/uploads/'):
                filepath = '/static' + filepath
            else:
                filepath = '/static/' + filepath.lstrip('/')

        return filepath

    return jsonify({
        'media': [{
            'id': m.id,
            'filename': m.filename,
            'original_filename': m.original_filename,
            'filepath': normalize_filepath(m),
            'width': m.width or 0,
            'height': m.height or 0,
            'album': m.album or ''
        } for m in media_list],
        'albums': album_names
    })


# ==================== QUẢN LÝ DỰ ÁN ====================
@admin_bp.route('/projects')
@permission_required('view_projects')  # ✅ Xem dự án
def projects():
    """Danh sách dự án"""
    page = request.args.get('page', 1, type=int)
    projects = Project.query.order_by(Project.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/projects.html', projects=projects)


@admin_bp.route('/projects/add', methods=['GET', 'POST'])
@permission_required('manage_projects')  # ✅ Quản lý dự án
def add_project():
    """Thêm dự án mới"""
    form = ProjectForm()

    if form.validate_on_submit():
        image_path = get_image_from_form(form.image, 'image', folder='projects')

        project = Project(
            title=form.title.data,
            slug=form.slug.data,
            client=form.client.data,
            location=form.location.data,
            year=form.year.data,
            description=form.description.data,
            content=form.content.data,
            image=image_path,
            project_type=form.project_type.data,
            area=form.area.data,
            products_used=form.products_used.data,
            is_featured=form.is_featured.data,
            is_active=form.is_active.data
        )

        db.session.add(project)
        db.session.commit()

        flash('Đã thêm dự án thành công!', 'success')
        return redirect(url_for('admin.projects'))

    return render_template('admin/project_form.html', form=form, title='Thêm dự án')


@admin_bp.route('/projects/edit/<int:id>', methods=['GET', 'POST'])
@permission_required('manage_projects')  # ✅ Quản lý dự án
def edit_project(id):
    """Sửa dự án"""
    project = Project.query.get_or_404(id)
    form = ProjectForm(obj=project)

    if form.validate_on_submit():
        new_image = get_image_from_form(form.image, 'image', folder='projects')
        if new_image:
            project.image = new_image

        project.title = form.title.data
        project.slug = form.slug.data
        project.client = form.client.data
        project.location = form.location.data
        project.year = form.year.data
        project.description = form.description.data
        project.content = form.content.data
        project.project_type = form.project_type.data
        project.area = form.area.data
        project.products_used = form.products_used.data
        project.is_featured = form.is_featured.data
        project.is_active = form.is_active.data

        db.session.commit()

        flash('Đã cập nhật dự án thành công!', 'success')
        return redirect(url_for('admin.projects'))

    return render_template('admin/project_form.html', form=form, title='Sửa dự án', project=project)


@admin_bp.route('/projects/delete/<int:id>')
@permission_required('manage_projects')  # ✅ Quản lý dự án
def delete_project(id):
    """Xóa dự án"""
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()

    flash('Đã xóa dự án thành công!', 'success')
    return redirect(url_for('admin.projects'))


# ==================== QUẢN LÝ TUYỂN DỤNG ====================
@admin_bp.route('/jobs')
@permission_required('view_jobs')  # ✅ Xem tuyển dụng
def jobs():
    """Danh sách tuyển dụng"""
    page = request.args.get('page', 1, type=int)
    jobs = Job.query.order_by(Job.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/jobs.html', jobs=jobs)


@admin_bp.route('/jobs/add', methods=['GET', 'POST'])
@permission_required('manage_jobs')  # ✅ Quản lý tuyển dụng
def add_job():
    """Thêm tin tuyển dụng mới"""
    form = JobForm()

    if form.validate_on_submit():
        job = Job(
            title=form.title.data,
            slug=form.slug.data,
            department=form.department.data,
            location=form.location.data,
            job_type=form.job_type.data,
            level=form.level.data,
            salary=form.salary.data,
            experience=form.experience.data,
            description=form.description.data,
            requirements=form.requirements.data,
            benefits=form.benefits.data,
            deadline=form.deadline.data,
            contact_email=form.contact_email.data,
            is_active=form.is_active.data,
            is_urgent=form.is_urgent.data
        )

        db.session.add(job)
        db.session.commit()

        flash('Đã thêm tin tuyển dụng thành công!', 'success')
        return redirect(url_for('admin.jobs'))

    return render_template('admin/job_form.html', form=form, title='Thêm tin tuyển dụng')


@admin_bp.route('/jobs/edit/<int:id>', methods=['GET', 'POST'])
@permission_required('manage_jobs')  # ✅ Quản lý tuyển dụng
def edit_job(id):
    """Sửa tin tuyển dụng"""
    job = Job.query.get_or_404(id)
    form = JobForm(obj=job)

    if form.validate_on_submit():
        job.title = form.title.data
        job.slug = form.slug.data
        job.department = form.department.data
        job.location = form.location.data
        job.job_type = form.job_type.data
        job.level = form.level.data
        job.salary = form.salary.data
        job.experience = form.experience.data
        job.description = form.description.data
        job.requirements = form.requirements.data
        job.benefits = form.benefits.data
        job.deadline = form.deadline.data
        job.contact_email = form.contact_email.data
        job.is_active = form.is_active.data
        job.is_urgent = form.is_urgent.data

        db.session.commit()

        flash('Đã cập nhật tin tuyển dụng thành công!', 'success')
        return redirect(url_for('admin.jobs'))

    return render_template('admin/job_form.html', form=form, title='Sửa tin tuyển dụng', job=job)


@admin_bp.route('/jobs/delete/<int:id>')
@permission_required('manage_jobs')  # ✅ Quản lý tuyển dụng
def delete_job(id):
    """Xóa tin tuyển dụng"""
    job = Job.query.get_or_404(id)
    db.session.delete(job)
    db.session.commit()

    flash('Đã xóa tin tuyển dụng thành công!', 'success')
    return redirect(url_for('admin.jobs'))


# ==================== QUẢN LÝ ROLES & PERMISSIONS ====================

@admin_bp.route('/roles')
@permission_required('manage_roles')  # ✅ Quản lý phân quyền
def roles():
    """Danh sách roles"""
    roles = Role.query.order_by(Role.priority.desc()).all()

    stats = {
        'total_roles': Role.query.count(),
        'total_permissions': Permission.query.count(),
        'total_users': User.query.count(),
        'active_roles': Role.query.filter_by(is_active=True).count()
    }

    return render_template('admin/roles.html', roles=roles, stats=stats)


@admin_bp.route('/roles/add', methods=['GET', 'POST'])
@permission_required('manage_roles')  # ✅ Quản lý phân quyền
def add_role():
    """Thêm role mới"""
    form = RoleForm()

    if form.validate_on_submit():
        existing = Role.query.filter_by(name=form.name.data).first()
        if existing:
            flash('Tên role đã tồn tại!', 'danger')
            return render_template('admin/role_form.html', form=form, title='Thêm vai trò')

        role = Role(
            name=form.name.data,
            display_name=form.display_name.data,
            description=form.description.data,
            priority=form.priority.data,
            color=form.color.data,
            is_active=form.is_active.data
        )

        db.session.add(role)
        db.session.commit()

        flash(f'Đã tạo vai trò "{role.display_name}" thành công!', 'success')
        return redirect(url_for('admin.roles'))

    return render_template('admin/role_form.html', form=form, title='Thêm vai trò')


@admin_bp.route('/roles/edit/<int:id>', methods=['GET', 'POST'])
@permission_required('manage_roles')  # ✅ Quản lý phân quyền
def edit_role(id):
    """Sửa role"""
    role = Role.query.get_or_404(id)
    form = RoleForm(obj=role)

    if form.validate_on_submit():
        if role.name in ['admin', 'user'] and form.name.data != role.name:
            flash('Không thể đổi tên role hệ thống!', 'danger')
            return render_template('admin/role_form.html', form=form, title='Sửa vai trò', role=role)

        role.name = form.name.data
        role.display_name = form.display_name.data
        role.description = form.description.data
        role.priority = form.priority.data
        role.color = form.color.data
        role.is_active = form.is_active.data

        db.session.commit()

        flash(f'Đã cập nhật vai trò "{role.display_name}" thành công!', 'success')
        return redirect(url_for('admin.roles'))

    return render_template('admin/role_form.html', form=form, title='Sửa vai trò', role=role)


@admin_bp.route('/roles/delete/<int:id>')
@permission_required('manage_roles')  # ✅ Quản lý phân quyền
def delete_role(id):
    """Xóa role"""
    role = Role.query.get_or_404(id)

    if role.name in ['admin', 'user']:
        flash('Không thể xóa role hệ thống!', 'danger')
        return redirect(url_for('admin.roles'))

    if role.users.count() > 0:
        flash(f'Không thể xóa role có {role.users.count()} người dùng!', 'danger')
        return redirect(url_for('admin.roles'))

    db.session.delete(role)
    db.session.commit()

    flash(f'Đã xóa vai trò "{role.display_name}" thành công!', 'success')
    return redirect(url_for('admin.roles'))


@admin_bp.route('/roles/<int:id>/permissions', methods=['GET', 'POST'])
@permission_required('manage_roles')  # ✅ Quản lý phân quyền
def edit_role_permissions(id):
    """Chỉnh sửa permissions của role"""
    role = Role.query.get_or_404(id)

    all_permissions = Permission.query.filter_by(is_active=True).order_by(
        Permission.category, Permission.name
    ).all()

    perms_by_category = {}
    for perm in all_permissions:
        cat = perm.category or 'other'
        if cat not in perms_by_category:
            perms_by_category[cat] = []
        perms_by_category[cat].append(perm)

    current_perm_ids = [p.id for p in role.permissions.all()]

    if request.method == 'POST':
        selected_perm_ids = request.form.getlist('permissions')
        selected_perm_ids = [int(pid) for pid in selected_perm_ids]

        role.permissions = []

        for perm_id in selected_perm_ids:
            perm = Permission.query.get(perm_id)
            if perm:
                role.add_permission(perm)

        db.session.commit()

        flash(f'Đã cập nhật quyền cho vai trò "{role.display_name}"', 'success')
        return redirect(url_for('admin.roles'))

    return render_template('admin/edit_role_permissions.html',
                           role=role,
                           perms_by_category=perms_by_category,
                           current_perm_ids=current_perm_ids)


@admin_bp.route('/permissions')
@permission_required('manage_roles')  # ✅ Quản lý phân quyền
def permissions():
    """Danh sách permissions"""
    all_permissions = Permission.query.order_by(Permission.category, Permission.name).all()

    perms_by_category = {}
    for perm in all_permissions:
        cat = perm.category or 'other'
        if cat not in perms_by_category:
            perms_by_category[cat] = []
        perms_by_category[cat].append(perm)

    return render_template('admin/permissions.html', perms_by_category=perms_by_category)


@admin_bp.route('/permissions/add', methods=['GET', 'POST'])
@permission_required('manage_roles')  # ✅ Quản lý phân quyền
def add_permission():
    """Thêm permission mới"""
    form = PermissionForm()

    if form.validate_on_submit():
        existing = Permission.query.filter_by(name=form.name.data).first()
        if existing:
            flash('Tên permission đã tồn tại!', 'danger')
            return render_template('admin/permission_form.html', form=form, title='Thêm quyền')

        perm = Permission(
            name=form.name.data,
            display_name=form.display_name.data,
            description=form.description.data,
            category=form.category.data,
            icon=form.icon.data or 'bi-key',
            is_active=form.is_active.data
        )

        db.session.add(perm)
        db.session.commit()

        flash(f'Đã tạo quyền "{perm.display_name}" thành công!', 'success')
        return redirect(url_for('admin.permissions'))

    return render_template('admin/permission_form.html', form=form, title='Thêm quyền')