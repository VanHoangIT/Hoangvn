"""
SEO Keywords Configuration
Dễ dàng chỉnh sửa keywords mà không cần sửa code logic
"""

# Keywords cho Media/Image SEO
MEDIA_KEYWORDS = {
    'primary': [
        'máy lọc nước',
        'a.o smith',
        'ao smith',
        'hoang.com.vn'
    ],
    'secondary': [
        'lọc nước',
        'máy lọc',
        'thiết bị lọc',
        'bộ lọc nước'
    ],
    'brand': [
        'a.o',
        'smith',
        'aosmith'
    ],
    'general': [
        'sản phẩm',
        'thiết bị',
        'dịch vụ',
        'máy',
        'nước'
    ]
}

# Scoring weights (có thể tùy chỉnh)
KEYWORD_SCORES = {
    'primary': 20,      # Full score nếu có primary keyword
    'secondary_brand': 17,  # Secondary + Brand
    'secondary': 12,    # Chỉ có secondary
    'brand': 8,         # Chỉ có brand
    'general': 5        # Chỉ có general keywords
}