from flask import Blueprint, render_template, request, flash, redirect, url_for
from app import db
from app.models import Product, Category, Banner, Blog, FAQ, Contact, Project, Job  # ← Thêm Project, Job
from app.forms import ContactForm
from sqlalchemy import or_
from app.project_config import PROJECT_TYPES

# Tạo Blueprint cho frontend
main_bp = Blueprint('main', __name__)


# ==================== TRANG CHỦ ====================
@main_bp.route('/')
def index():
    """Trang chủ"""
    # Lấy banners đang active
    banners = Banner.query.filter_by(is_active=True).order_by(Banner.order).all()

    # Lấy sản phẩm nổi bật (featured)
    featured_products = Product.query.filter_by(
        is_featured=True,
        is_active=True
    ).limit(8).all()

    # Lấy sản phẩm mới nhất
    latest_products = Product.query.filter_by(
        is_active=True
    ).order_by(Product.created_at.desc()).limit(8).all()

    # Lấy tin tức nổi bật
    featured_blogs = Blog.query.filter_by(
        is_featured=True,
        is_active=True
    ).limit(3).all()

    featured_projects = Project.query.filter_by(is_featured=True, is_active=True).order_by(Project.created_at.desc()).all()

    return render_template('index.html',
                           banners=banners,
                           featured_products=featured_products,
                           latest_products=latest_products,
                           featured_blogs=featured_blogs,
                           featured_projects=featured_projects)


# ==================== GIỚI THIỆU ====================
@main_bp.route('/about')
def about():
    """Trang giới thiệu"""
    return render_template('about.html')


# ==================== SẢN PHẨM ====================
@main_bp.route('/products')
def products():
    """Trang danh sách sản phẩm với filter"""
    page = request.args.get('page', 1, type=int)
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'latest')

    # Query cơ bản
    query = Product.query.filter_by(is_active=True)

    # Filter theo danh mục
    if category_id:
        query = query.filter_by(category_id=category_id)

    # Search theo tên
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))

    # Sắp xếp
    if sort == 'latest':
        query = query.order_by(Product.created_at.desc())
    elif sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort == 'popular':
        query = query.order_by(Product.views.desc())

    # Phân trang
    pagination = query.paginate(
        page=page,
        per_page=12,
        error_out=False
    )

    products = pagination.items
    categories = Category.query.filter_by(is_active=True).all()

    return render_template('products.html',
                           products=products,
                           categories=categories,
                           pagination=pagination,
                           current_category=category_id,
                           current_search=search,
                           current_sort=sort)


@main_bp.route('/product/<slug>')
def product_detail(slug):
    """Trang chi tiết sản phẩm"""
    product = Product.query.filter_by(slug=slug, is_active=True).first_or_404()

    # Tăng lượt xem
    product.views += 1
    db.session.commit()

    # Lấy sản phẩm liên quan (cùng danh mục)
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.is_active == True
    ).limit(4).all()

    return render_template('product_detail.html',
                           product=product,
                           related_products=related_products)


# ==================== TIN TỨC / BLOG ====================
@main_bp.route('/blog')
def blog():
    """Trang danh sách blog"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')

    # Query
    query = Blog.query.filter_by(is_active=True)

    # Search
    if search:
        query = query.filter(
            or_(
                Blog.title.ilike(f'%{search}%'),
                Blog.excerpt.ilike(f'%{search}%')
            )
        )

    # Sắp xếp mới nhất
    query = query.order_by(Blog.created_at.desc())

    # Phân trang
    pagination = query.paginate(
        page=page,
        per_page=9,
        error_out=False
    )

    blogs = pagination.items

    # Bài viết nổi bật sidebar
    featured_blogs = Blog.query.filter_by(
        is_featured=True,
        is_active=True
    ).limit(5).all()

    return render_template('blog.html',
                           blogs=blogs,
                           pagination=pagination,
                           featured_blogs=featured_blogs,
                           current_search=search)


@main_bp.route('/blog/<slug>')
def blog_detail(slug):
    """Trang chi tiết blog"""
    blog = Blog.query.filter_by(slug=slug, is_active=True).first_or_404()

    # Tăng lượt xem
    blog.views += 1
    db.session.commit()

    # Bài viết liên quan
    related_blogs = Blog.query.filter(
        Blog.id != blog.id,
        Blog.is_active == True
    ).order_by(Blog.created_at.desc()).limit(3).all()

    return render_template('blog_detail.html',
                           blog=blog,
                           related_blogs=related_blogs)


# ==================== LIÊN HỆ ====================
@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Trang liên hệ"""
    form = ContactForm()

    if form.validate_on_submit():
        # Tạo contact mới
        contact = Contact(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            subject=form.subject.data,
            message=form.message.data
        )

        db.session.add(contact)
        db.session.commit()

        flash('Cảm ơn bạn đã liên hệ! Chúng tôi sẽ phản hồi sớm nhất.', 'success')
        return redirect(url_for('main.contact'))

    return render_template('contact.html', form=form)


# ==================== CHÍNH SÁCH ====================
@main_bp.route('/policy')
def policy():
    """Trang chính sách"""
    return render_template('policy.html')


# ==================== FAQ ====================
@main_bp.route('/faq')
def faq():
    """Trang câu hỏi thường gặp"""
    faqs = FAQ.query.filter_by(is_active=True).order_by(FAQ.order).all()
    return render_template('faq.html', faqs=faqs)


# ==================== SEARCH ====================
@main_bp.route('/search')
def search():
    """Trang tìm kiếm tổng hợp"""
    keyword = request.args.get('q', '')

    if not keyword:
        return redirect(url_for('main.index'))

    # Tìm sản phẩm
    products = Product.query.filter(
        Product.name.ilike(f'%{keyword}%'),
        Product.is_active == True
    ).limit(10).all()

    # Tìm blog
    blogs = Blog.query.filter(
        or_(
            Blog.title.ilike(f'%{keyword}%'),
            Blog.excerpt.ilike(f'%{keyword}%')
        ),
        Blog.is_active == True
    ).limit(5).all()

    return render_template('search.html',
                           keyword=keyword,
                           products=products,
                           blogs=blogs)


@main_bp.route('/projects')
def projects():
    """Trang danh sách dự án"""
    page = request.args.get('page', 1, type=int)
    project_type = request.args.get('type', '')

    query = Project.query.filter_by(is_active=True)

    if project_type:
        query = query.filter_by(project_type=project_type)

    projects = query.order_by(Project.year.desc()).paginate(
        page=page, per_page=12, error_out=False
    )

    featured_projects = Project.query.filter_by(is_featured=True, is_active=True).limit(6).all()

    return render_template('projects.html',
                           projects=projects,
                           featured_projects=featured_projects,
                           project_types=PROJECT_TYPES,
                           current_type=project_type)


@main_bp.route('/projects/<slug>')
def project_detail(slug):
    """Trang chi tiết dự án"""
    project = Project.query.filter_by(slug=slug, is_active=True).first_or_404()

    # Tăng lượt xem
    project.view_count += 1
    db.session.commit()

    # Dự án liên quan
    related = Project.query.filter(
        Project.id != project.id,
        Project.project_type == project.project_type,
        Project.is_active == True
    ).limit(4).all()

    return render_template('project_detail.html',
                           project=project,
                           related=related)


@main_bp.route('/careers')
def careers():
    """Trang tuyển dụng"""
    department = request.args.get('dept', '')
    location = request.args.get('loc', '')

    query = Job.query.filter_by(is_active=True)

    if department:
        query = query.filter_by(department=department)
    if location:
        query = query.filter_by(location=location)

    jobs = query.order_by(Job.is_urgent.desc(), Job.created_at.desc()).all()

    # Lấy danh sách phòng ban và địa điểm unique
    departments = db.session.query(Job.department).filter_by(is_active=True).distinct().all()
    locations = db.session.query(Job.location).filter_by(is_active=True).distinct().all()

    return render_template('careers.html',
                           jobs=jobs,
                           departments=[d[0] for d in departments if d[0]],
                           locations=[l[0] for l in locations if l[0]])


@main_bp.route('/careers/<slug>')
def job_detail(slug):
    """Trang chi tiết tuyển dụng"""
    job = Job.query.filter_by(slug=slug, is_active=True).first_or_404()

    # Tăng lượt xem
    job.view_count += 1
    db.session.commit()

    # Các vị trí khác
    other_jobs = Job.query.filter(
        Job.id != job.id,
        Job.is_active == True
    ).order_by(Job.is_urgent.desc()).limit(5).all()

    return render_template('job_detail.html',
                           job=job,
                           other_jobs=other_jobs)