from datetime import datetime
from app import db
from app.models import User
from werkzeug.security import generate_password_hash


def seed_staff_data():
    """Tạo tài khoản quản trị viên (staff) mặc định"""
    fixed_date = datetime(2025, 10, 1, 8, 0, 0)

    staff_list = [
        {
            "username": "admin",
            "email": "admin@hoang.com.vn",
            "password": "admin@hoang123",
            "is_admin": True
        },
        {
            "username": "van_hoang",
            "email": "vuvanhoang.1607@gmail.com",
            "password": "123456",
            "is_admin": True
        }
    ]

    for staff in staff_list:
        existing_user = User.query.filter_by(email=staff["email"]).first()
        if not existing_user:
            user = User(
                username=staff["username"],
                email=staff["email"],
                is_admin=staff["is_admin"],
                created_at=fixed_date
            )
            # ✅ Hash password trước khi lưu
            user.password_hash = generate_password_hash(staff["password"])
            db.session.add(user)
            print(f"✅ Đã tạo user: {staff['username']} ({staff['email']})")

    db.session.commit()
    print("✅ Đã seed dữ liệu tài khoản staff thành công!")


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        seed_staff_data()