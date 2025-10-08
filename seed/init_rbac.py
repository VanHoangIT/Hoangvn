"""
Script khởi tạo RBAC: Roles, Permissions và migrate users cũ
Chạy: python seed/init_rbac.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User
from app.models_rbac import Role, Permission, init_default_roles, init_default_permissions, assign_default_permissions


def migrate_old_users():
    print("\n🔄 Migrating old users...")
    admin_role = Role.query.filter_by(name='admin').first()
    user_role = Role.query.filter_by(name='user').first()
    if not admin_role or not user_role:
        print("❌ Error: Roles not found! Run init_roles first.")
        return

    users_without_role = User.query.filter_by(role_id=None).all()
    if not users_without_role:
        print("✓ No users to migrate")
        return

    migrated_count = 0
    for user in users_without_role:
        try:
            if getattr(user, 'is_admin', False):
                user.role_id = admin_role.id
                print(f"  → {user.username}: Admin")
            else:
                user.role_id = user_role.id
                print(f"  → {user.username}: User")
        except Exception:
            user.role_id = user_role.id
            print(f"  → {user.username}: User (default)")
        migrated_count += 1

    db.session.commit()
    print(f"✅ Migrated {migrated_count} users")



def create_test_users():
    """Tạo users test cho từng role (nếu chưa có)"""
    print("\n👥 Creating test users...")

    test_users = [
        {
            'username': 'admin',
            'email': 'admin@example.com',
            'password': 'admin123',
            'role': 'admin'
        },
        {
            'username': 'editor',
            'email': 'editor@example.com',
            'password': 'editor123',
            'role': 'editor'
        },
        {
            'username': 'moderator',
            'email': 'moderator@example.com',
            'password': 'mod123',
            'role': 'moderator'
        },
        {
            'username': 'testuser',
            'email': 'user@example.com',
            'password': 'user123',
            'role': 'user'
        }
    ]

    created_count = 0
    for user_data in test_users:
        existing = User.query.filter_by(username=user_data['username']).first()
        if existing:
            print(f"  ⚠ User '{user_data['username']}' already exists")
            continue

        role = Role.query.filter_by(name=user_data['role']).first()
        if not role:
            print(f"  ❌ Role '{user_data['role']}' not found")
            continue

        user = User(
            username=user_data['username'],
            email=user_data['email'],
            role_id=role.id
        )
        user.set_password(user_data['password'])
        db.session.add(user)
        created_count += 1
        print(f"  ✓ Created: {user_data['username']} ({user_data['role']})")

    if created_count > 0:
        db.session.commit()
        print(f"✅ Created {created_count} test users")
    else:
        print("✓ No new users created")


def show_rbac_summary():
    """Hiển thị tóm tắt RBAC sau khi setup"""
    print("\n" + "=" * 60)
    print("📊 RBAC SUMMARY")
    print("=" * 60)

    roles = Role.query.order_by(Role.priority.desc()).all()
    for role in roles:
        print(f"\n🎭 {role.display_name} ({role.name})")
        print(f"   Priority: {role.priority} | Users: {role.user_count}")
        print(f"   Permissions: {role.permissions.count()}")

        # Show first 5 permissions
        perms = role.permissions.limit(5).all()
        for p in perms:
            print(f"     - {p.display_name}")
        if role.permissions.count() > 5:
            print(f"     ... and {role.permissions.count() - 5} more")

    print("\n" + "=" * 60)
    print("✅ RBAC Setup Complete!")
    print("=" * 60)

    print("\n📝 Test Login Credentials:")
    print("  Admin:     admin@example.com / admin123")
    print("  Editor:    editor@example.com / editor123")
    print("  Moderator: moderator@example.com / mod123")
    print("  User:      user@example.com / user123")
    print()


def main():
    """Main function"""
    app = create_app()

    with app.app_context():
        print("\n🚀 Starting RBAC Initialization...")
        print("=" * 60)

        # Step 1: Create Roles
        print("\n1️⃣ Creating Roles...")
        init_default_roles()

        # Step 2: Create Permissions
        print("\n2️⃣ Creating Permissions...")
        init_default_permissions()

        # Step 3: Assign Permissions to Roles
        print("\n3️⃣ Assigning Permissions to Roles...")
        assign_default_permissions()

        # Step 4: Migrate Old Users
        print("\n4️⃣ Migrating Existing Users...")
        migrate_old_users()

        # Step 5: Create Test Users (optional)
        create_test = input("\n❓ Create test users? (y/n): ").lower() == 'y'
        if create_test:
            create_test_users()

        # Step 6: Show Summary
        show_rbac_summary()


if __name__ == '__main__':
    main()