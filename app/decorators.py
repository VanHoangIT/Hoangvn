# ============= Quản lí quyền admin/user =============
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def admin_required(f):
    """Decorator yêu cầu quyền admin"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Vui lòng đăng nhập!', 'warning')
            return redirect(url_for('admin.login'))

        if not current_user.is_admin:
            flash('Bạn không có quyền truy cập chức năng này!', 'danger')
            return redirect(url_for('admin.dashboard'))

        return f(*args, **kwargs)

    return decorated_function