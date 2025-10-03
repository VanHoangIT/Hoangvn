import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Category, Product, Banner, Blog, FAQ, Contact
import datetime

app = create_app()

with app.app_context():
    print("🚀 Bắt đầu seed dữ liệu...")

    # ==================== ADMIN USER ====================
    if not User.query.filter_by(email="admin@catsay.vn").first():
        admin = User(
            username="admin",
            email="admin@example.com",
            is_admin=True
        )
        admin.set_password("admin123")
        db.session.add(admin)
        print("✅ Admin user created")
    else:
        print("⚠️  Admin already exists")

    db.session.commit()

    # ==================== CATEGORIES ====================
    categories_data = [
        {
            'name': 'Cát Xây Dựng',
            'slug': 'cat-xay-dung',
            'description': 'Cát xây dựng chất lượng cao cho công trình'
        },
        {
            'name': 'Cát Tô',
            'slug': 'cat-to',
            'description': 'Cát tô mịn, phù hợp hoàn thiện bề mặt'
        },
        {
            'name': 'Cát Sàng',
            'slug': 'cat-sang',
            'description': 'Cát sàng đạt chuẩn, độ mịn cao'
        },
        {
            'name': 'Cát Thô',
            'slug': 'cat-tho',
            'description': 'Cát thô dùng cho móng, đổ bê tông'
        }
    ]

    for cat_data in categories_data:
        if not Category.query.filter_by(slug=cat_data['slug']).first():
            cat = Category(**cat_data, is_active=True)
            db.session.add(cat)
            print(f"✅ Category: {cat_data['name']}")

    db.session.commit()

    # ==================== PRODUCTS ====================
    products_data = [
        {
            'name': 'Cát Xây Dựng Hạt To',
            'slug': 'cat-xay-dung-hat-to',
            'description': 'Cát xây dựng hạt to, độ bám dính cao, phù hợp xây tường, đổ móng',
            'price': 180000,
            'old_price': 200000,
            'category_id': 1,
            'is_featured': True
        },
        {
            'name': 'Cát Xây Dựng Hạt Vừa',
            'slug': 'cat-xay-dung-hat-vua',
            'description': 'Cát xây dựng hạt vừa, đa năng cho mọi công trình',
            'price': 170000,
            'category_id': 1,
            'is_featured': True
        },
        {
            'name': 'Cát Tô Tường Mịn',
            'slug': 'cat-to-tuong-min',
            'description': 'Cát tô mịn, độ mịn cao, bề mặt hoàn thiện đẹp',
            'price': 190000,
            'old_price': 210000,
            'category_id': 2,
            'is_featured': True
        },
        {
            'name': 'Cát Tô Ngoại Thất',
            'slug': 'cat-to-ngoai-that',
            'description': 'Cát tô chuyên dụng ngoại thất, chống thấm tốt',
            'price': 195000,
            'category_id': 2
        },
        {
            'name': 'Cát Sàng Cao Cấp',
            'slug': 'cat-sang-cao-cap',
            'description': 'Cát sàng qua nhiều công đoạn, đạt tiêu chuẩn cao',
            'price': 210000,
            'category_id': 3
        },
        {
            'name': 'Cát Thô Đổ Móng',
            'slug': 'cat-tho-do-mong',
            'description': 'Cát thô chuyên dụng đổ móng, kết cấu chịu lực',
            'price': 160000,
            'category_id': 4
        },
        {
            'name': 'Cát Thô Đổ Bê Tông',
            'slug': 'cat-tho-do-be-tong',
            'description': 'Cát thô cho bê tông, độ bền cao',
            'price': 165000,
            'category_id': 4
        }
    ]

    for prod_data in products_data:
        if not Product.query.filter_by(slug=prod_data['slug']).first():
            prod = Product(**prod_data, is_active=True)
            db.session.add(prod)
            print(f"✅ Product: {prod_data['name']}")

    db.session.commit()

    # ==================== BANNERS ====================
    banners_data = [
        {
            'title': 'Cát Xây Dựng Chất Lượng Cao',
            'subtitle': 'Giá tốt nhất thị trường - Giao hàng nhanh chóng',
            'button_text': 'Xem Ngay',
            'link': '/products',
            'order': 1
        },
        {
            'title': 'Cát Tô Mịn - Hoàn Thiện Hoàn Hảo',
            'subtitle': 'Chuyên cung cấp cát tô cho công trình lớn nhỏ',
            'button_text': 'Liên Hệ',
            'link': '/contact',
            'order': 2
        }
    ]

    for banner_data in banners_data:
        if not Banner.query.filter_by(title=banner_data['title']).first():
            banner = Banner(**banner_data, is_active=True)
            db.session.add(banner)
            print(f"✅ Banner: {banner_data['title']}")

    db.session.commit()

    # ==================== BLOGS ====================
    blogs_data = [
        {
            'title': 'Cách chọn cát xây dựng chất lượng cho công trình',
            'slug': 'cach-chon-cat-xay-dung-chat-luong',
            'excerpt': 'Hướng dẫn chi tiết cách chọn cát xây dựng đạt chuẩn, phù hợp với từng loại công trình',
            'content': '''<p>Cát xây dựng là vật liệu quan trọng, chiếm 30-40% thành phần trong vữa và bê tông. Việc chọn cát đúng chuẩn ảnh hưởng trực tiếp đến chất lượng công trình.</p>
            <h2>Tiêu chí chọn cát xây dựng</h2>
            <p>1. <strong>Độ sạch:</strong> Cát phải sạch, không lẫn bùn, đất, tạp chất hữu cơ</p>
            <p>2. <strong>Hạt cát:</strong> Kích thước hạt đều, không quá mịn hoặc quá thô</p>
            <p>3. <strong>Màu sắc:</strong> Cát tốt có màu vàng nhạt, không đen sẫm</p>
            <h2>Phân loại cát xây dựng</h2>
            <p>- Cát thô: dùng đổ móng, bê tông kết cấu</p>
            <p>- Cát vừa: xây tường, trát tường thô</p>
            <p>- Cát mịn: tô tường, hoàn thiện bề mặt</p>''',
            'author': 'Admin',
            'is_featured': True,
            'focus_keyword': 'cát xây dựng',
            'meta_title': 'Cách chọn cát xây dựng chất lượng | Cát Sấy',
            'meta_description': 'Hướng dẫn chi tiết cách chọn cát xây dựng đạt chuẩn cho công trình. Tư vấn miễn phí, giá tốt nhất thị trường.'
        },
        {
            'title': 'Phân biệt cát tô và cát xây - Chọn loại nào cho công trình?',
            'slug': 'phan-biet-cat-to-va-cat-xay',
            'excerpt': 'So sánh chi tiết giữa cát tô và cát xây, giúp bạn lựa chọn đúng loại cát cho công trình',
            'content': '''<p>Nhiều người thắc mắc về sự khác biệt giữa cát tô và cát xây. Bài viết này sẽ giải đáp chi tiết.</p>
            <h2>Cát xây là gì?</h2>
            <p>Cát xây có hạt to hơn, độ bám dính cao, dùng cho các công đoạn xây gạch, đổ móng, làm vữa.</p>
            <h2>Cát tô là gì?</h2>
            <p>Cát tô có hạt mịn hơn, được sàng kỹ, dùng cho công đoạn hoàn thiện bề mặt tường.</p>
            <h2>Nên chọn loại nào?</h2>
            <p>- Xây tường gạch → dùng cát xây</p>
            <p>- Tô tường trong nhà → dùng cát tô mịn</p>
            <p>- Tô tường ngoài → dùng cát tô có độ hạt vừa</p>''',
            'author': 'Admin',
            'focus_keyword': 'cát tô',
            'meta_title': 'Phân biệt cát tô và cát xây | Tư vấn chọn cát',
            'meta_description': 'So sánh chi tiết cát tô và cát xây. Tư vấn chọn loại cát phù hợp cho từng công trình xây dựng.'
        },
        {
            'title': 'Bảng giá cát xây dựng mới nhất 2025',
            'slug': 'bang-gia-cat-xay-dung-2025',
            'excerpt': 'Cập nhật bảng giá cát xây dựng, cát tô, cát sàng mới nhất thị trường năm 2025',
            'content': '''<p>Giá cát xây dựng dao động tùy theo từng loại, chất lượng và khu vực.</p>
            <h2>Bảng giá cát xây dựng 2025</h2>
            <p>- Cát xây hạt to: 180,000 - 200,000đ/m³</p>
            <p>- Cát xây hạt vừa: 170,000 - 190,000đ/m³</p>
            <p>- Cát tô mịn: 190,000 - 220,000đ/m³</p>
            <p>- Cát sàng cao cấp: 210,000 - 240,000đ/m³</p>
            <p>- Cát thô: 160,000 - 180,000đ/m³</p>
            <h2>Lưu ý khi mua cát</h2>
            <p>Giá cát có thể thay đổi theo mùa vụ, khu vực và khối lượng đặt hàng. Đặt hàng số lượng lớn sẽ được giảm giá.</p>''',
            'author': 'Admin',
            'focus_keyword': 'giá cát xây dựng',
            'meta_title': 'Bảng giá cát xây dựng 2025 | Giá tốt nhất',
            'meta_description': 'Bảng giá cát xây dựng, cát tô, cát sàng mới nhất 2025. Giao hàng nhanh, giá tốt nhất thị trường.'
        }
    ]

    for blog_data in blogs_data:
        if not Blog.query.filter_by(slug=blog_data['slug']).first():
            blog = Blog(**blog_data, is_active=True)
            blog.calculate_reading_time()
            db.session.add(blog)
            print(f"✅ Blog: {blog_data['title']}")

    db.session.commit()

    # ==================== FAQs ====================
    faqs_data = [
        {
            'question': 'Cát xây dựng có những loại nào?',
            'answer': 'Có 4 loại chính: Cát thô (đổ móng), Cát xây (xây tường), Cát tô (hoàn thiện), Cát sàng (cao cấp).',
            'order': 1
        },
        {
            'question': 'Giá cát xây dựng bao nhiêu tiền 1m³?',
            'answer': 'Giá dao động 160,000 - 220,000đ/m³ tùy loại. Liên hệ để có giá tốt nhất.',
            'order': 2
        },
        {
            'question': 'Làm sao biết cát chất lượng tốt?',
            'answer': 'Cát tốt có màu vàng nhạt, hạt đều, sạch, không bùn đất, độ ẩm vừa phải.',
            'order': 3
        },
        {
            'question': 'Có giao hàng tận nơi không?',
            'answer': 'Có, chúng tôi giao hàng tận công trình trong bán kính 50km.',
            'order': 4
        },
        {
            'question': '1 xe tải chở được bao nhiêu m³ cát?',
            'answer': 'Xe 5 tấn chở 3-4m³, xe 8 tấn chở 5-6m³, xe 15 tấn chở 10-12m³.',
            'order': 5
        }
    ]

    for faq_data in faqs_data:
        if not FAQ.query.filter_by(question=faq_data['question']).first():
            faq = FAQ(**faq_data, is_active=True)
            db.session.add(faq)
            print(f"✅ FAQ: {faq_data['question']}")

    db.session.commit()

    print("\n🎉 Seed hoàn tất!")
    print(f"📊 Thống kê:")
    print(f"  - Users: {User.query.count()}")
    print(f"  - Categories: {Category.query.count()}")
    print(f"  - Products: {Product.query.count()}")
    print(f"  - Banners: {Banner.query.count()}")
    print(f"  - Blogs: {Blog.query.count()}")
    print(f"  - FAQs: {FAQ.query.count()}")