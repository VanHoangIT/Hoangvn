"""
File cấu hình cho Project Types
Dễ dàng thay đổi các loại dự án mà không cần sửa code
"""

PROJECT_TYPES = [
    {
        'value': 'residential',
        'label': 'Nhà ở',
        'icon': 'bi-house',
        'description': 'Các dự án lắp đặt cho khu dân cư, biệt thự, chung cư'
    },
    {
        'value': 'office',
        'label': 'Văn phòng',
        'icon': 'bi-building',
        'description': 'Các dự án văn phòng, tòa nhà thương mại'
    },
    {
        'value': 'hotel',
        'label': 'Khách sạn',
        'icon': 'bi-building-fill',
        'description': 'Khách sạn, resort, nhà nghỉ'
    },
    {
        'value': 'restaurant',
        'label': 'Nhà hàng',
        'icon': 'bi-shop',
        'description': 'Nhà hàng, quán café, food court'
    },
    {
        'value': 'hospital',
        'label': 'Bệnh viện',
        'icon': 'bi-hospital',
        'description': 'Bệnh viện, phòng khám, trung tâm y tế'
    },
]

# Tạo choices cho WTForms (dùng trong ProjectForm)
PROJECT_TYPE_CHOICES = [(pt['value'], pt['label']) for pt in PROJECT_TYPES]

# Tạo dict để lookup nhanh
PROJECT_TYPE_DICT = {pt['value']: pt for pt in PROJECT_TYPES}