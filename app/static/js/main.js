// ==================== SCROLL TO TOP ====================
//window.addEventListener('scroll', function() {
    //const floatingButtons = document.querySelector('.floating-buttons');
    //if (floatingButtons) {
        //if (window.scrollY > 300) {
            //floatingButtons.style.display = 'flex';
        //} else {
            //floatingButtons.style.display = 'none';
        //}
    //}
//});

window.addEventListener('scroll', function() {
    const floatingButtons = document.querySelector('.floating-buttons');
    if (floatingButtons) {
        floatingButtons.style.display = 'flex'; // luôn hiển thị
    }
});


// ==================== ANIMATE ON SCROLL ====================
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate-on-scroll');
        }
    });
}, observerOptions);

// Observe all product cards and blog cards
document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.product-card, .blog-card');
    cards.forEach(card => {
        observer.observe(card);
    });
});

// ==================== AUTO DISMISS ALERTS ====================
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000); // Auto close after 5 seconds
    });
});

// ==================== SEARCH FORM VALIDATION ====================
document.addEventListener('DOMContentLoaded', function() {
    const searchForms = document.querySelectorAll('form[action*="search"]');
    searchForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const input = form.querySelector('input[name="q"], input[name="search"]');
            if (input && input.value.trim() === '') {
                e.preventDefault();
                alert('Vui lòng nhập từ khóa tìm kiếm');
            }
        });
    });
});

// ==================== IMAGE LAZY LOADING ====================
if ('loading' in HTMLImageElement.prototype) {
    const images = document.querySelectorAll('img[data-src]');
    images.forEach(img => {
        img.src = img.dataset.src;
    });
} else {
    // Fallback for browsers that don't support lazy loading
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/lazysizes/5.3.2/lazysizes.min.js';
    document.body.appendChild(script);
}

// ==================== SMOOTH SCROLL ====================
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#') {
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        }
    });
});
// ==================== BANNER AUTO SLIDE ====================
document.addEventListener('DOMContentLoaded', function() {
    const slides = document.querySelectorAll('.swiper-slide');
    let currentIndex = 0;

    if (slides.length > 0) {
        // Ẩn hết, chỉ hiện slide đầu tiên
        slides.forEach((slide, index) => {
            slide.style.display = index === 0 ? 'block' : 'none';
        });

        // Hàm đổi slide
        function showNextSlide() {
            slides[currentIndex].style.display = 'none';
            currentIndex = (currentIndex + 1) % slides.length;
            slides[currentIndex].style.display = 'block';
        }

        // Gọi interval chạy đều mỗi 3 giây
        setInterval(showNextSlide, 3000);
    }
});
