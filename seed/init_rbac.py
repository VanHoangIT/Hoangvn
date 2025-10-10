"""
===============================================================
 Script khởi tạo RBAC (Role-Based Access Control)
---------------------------------------------------------------
Nhiệm vụ:
    - Tạo các Roles (quyền hạn như admin, user, editor, moderator)
    - Tạo các Permissions (quyền thao tác cụ thể)
    - Gán Permissions cho từng Role
    - (Tuỳ chọn) Tạo các tài khoản test ứng với từng Role
    - Hiển thị tóm tắt cấu trúc RBAC sau khi khởi tạo
---------------------------------------------------------------
Cách chạy:
    python seed/init_rbac.py
===============================================================
"""

import sys
import os

# =============================================================
# 1️⃣ CẤU HÌNH ĐƯỜNG DẪN PYTHON
# -------------------------------------------------------------
# Mục đích: thêm thư mục gốc của project vào sys.path
# để có thể import được các module trong thư mục app/
# =============================================================

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# =============================================================
# 2️⃣ IMPORT CÁC MODULE CẦN THIẾT
# -------------------------------------------------------------
# - create_app: khởi tạo Flask app (theo mô hình factory)
# - db: đối tượng SQLAlchemy để thao tác DB
# - User: model người dùng
# - Role, Permission: model dùng cho hệ thống phân quyền RBAC
# - init_default_roles(): tạo các role mặc định
# - init_default_permissions(): tạo các permission mặc định
# - assign_default_permissions(): gán quyền cho từng role
# =============================================================

from app import create_app, db
from app.models import User
from app.models_rbac import Role, Permission, init_default_roles, init_default_permissions, assign_default_permissions


# =============================================================
# 3️⃣ HÀM TẠO NGƯỜI DÙNG TEST
# -------------------------------------------------------------
# Mục đích:
#   - Tạo sẵn các tài khoản test ứng với từng role (admin, editor, moderator, user)
#   - Dễ dàng kiểm tra chức năng phân quyền sau khi khởi tạo RBAC
# =============================================================

def create_test_users():
    """Tạo users test cho từng role (nếu chưa có)"""
    print("\n👥 Creating test users...")

    # Danh sách người dùng test cần tạo
    test_users = [
        {'username': 'admin', 'email': 'admin@example.com', 'password': 'admin123', 'role': 'admin'},
        {'username': 'editor', 'email': 'editor@example.com', 'password': 'editor123', 'role': 'editor'},
        {'username': 'moderator', 'email': 'moderator@example.com', 'password': 'mod123', 'role': 'moderator'},
        {'username': 'testuser', 'email': 'user@example.com', 'password': 'user123', 'role': 'user'}
    ]

    created_count = 0

    # Lặp qua từng user trong danh sách
    for user_data in test_users:
        # Kiểm tra nếu username đã tồn tại -> bỏ qua
        existing = User.query.filter_by(username=user_data['username']).first()
        if existing:
            print(f"  ⚠ User '{user_data['username']}' already exists")
            continue

        # Tìm role tương ứng trong DB
        role = Role.query.filter_by(name=user_data['role']).first()
        if not role:
            print(f"  ❌ Role '{user_data['role']}' not found — hãy chắc chắn đã init roles trước")
            continue

        # Tạo đối tượng User mới
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            role_id=role.id
        )
        user.set_password(user_data['password'])  # Mã hoá mật khẩu
        db.session.add(user)
        created_count += 1
        print(f"  ✓ Created: {user_data['username']} ({user_data['role']})")

    # Commit các user mới vào database
    if created_count > 0:
        db.session.commit()
        print(f"✅ Created {created_count} test users")
    else:
        print("✓ No new users created")


# =============================================================
# 4️⃣ HÀM HIỂN THỊ TÓM TẮT RBAC
# -------------------------------------------------------------
# Mục đích:
#   - In ra danh sách roles, permissions, số user thuộc mỗi role
#   - Giúp dev kiểm tra hệ thống RBAC đã setup thành công chưa
# =============================================================

def show_rbac_summary():
    """Hiển thị tóm tắt RBAC sau khi setup"""
    print("\n" + "=" * 60)
    print("📊 RBAC SUMMARY")
    print("=" * 60)

    # Lấy danh sách tất cả roles (ưu tiên role có priority cao)
    roles = Role.query.order_by(Role.priority.desc()).all()

    # Duyệt từng role và hiển thị thông tin
    for role in roles:
        print(f"\n🎭 {role.display_name} ({role.name})")
        print(f"   Priority: {role.priority} | Users: {role.user_count}")
        print(f"   Permissions: {role.permissions.count()}")

        # Hiển thị 5 permission đầu tiên của mỗi role (nếu có nhiều)
        perms = role.permissions.limit(5).all()
        for p in perms:
            print(f"     - {p.display_name}")
        if role.permissions.count() > 5:
            print(f"     ... and {role.permissions.count() - 5} more")

    # Hiển thị thông tin kết thúc và tài khoản test login
    print("\n" + "=" * 60)
    print("✅ RBAC Setup Complete!")
    print("=" * 60)

    print("\n📝 Test Login Credentials:")
    print("  Admin:     admin@example.com / admin123")
    print("  Editor:    editor@example.com / editor123")
    print("  Moderator: moderator@example.com / mod123")
    print("  User:      user@example.com / user123")
    print()


# =============================================================
# 5️⃣ HÀM CHÍNH (MAIN FUNCTION)
# -------------------------------------------------------------
# Mục đích:
#   - Tạo Flask app và mở context để làm việc với DB
#   - Gọi lần lượt các bước khởi tạo hệ thống RBAC
# =============================================================

def main():
    """Hàm chính khởi tạo RBAC"""
    app = create_app()  # Tạo ứng dụng Flask từ factory

    # Mở application context để có thể truy cập DB và models
    with app.app_context():
        print("\n🚀 Starting RBAC Initialization...")
        print("=" * 60)

        # Bước 1: Tạo Roles mặc định (admin, editor, moderator, user)
        print("\n1️⃣ Creating Roles...")
        init_default_roles()

        # Bước 2: Tạo Permissions mặc định (ví dụ: manage_users, view_products, v.v.)
        print("\n2️⃣ Creating Permissions...")
        init_default_permissions()

        # Bước 3: Gán Permissions cho từng Role
        print("\n3️⃣ Assigning Permissions to Roles...")
        assign_default_permissions()

        # (Tùy chọn) Bước 4: Tạo người dùng test nếu bạn muốn
        create_test = input("\n❓ Create test users? (y/n): ").lower() == 'y'
        if create_test:
            create_test_users()

        # Bước 5: Hiển thị kết quả tổng quan RBAC
        show_rbac_summary()


# =============================================================
# 6️⃣ ĐIỂM KHỞI CHẠY SCRIPT
# -------------------------------------------------------------
# Khi chạy file này trực tiếp (python seed/init_rbac.py),
# chương trình sẽ gọi hàm main().
# =============================================================

if __name__ == '__main__':
    main()
