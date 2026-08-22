{
    'name': 'Resale Attributes',
    'version': '19.0.1.0.0',
    'summary': 'Map configurable non-variant attributes to product template dropdowns',
    'category': 'Inventory/Resale',
    'author': 'Resale Project',
    'license': 'LGPL-3',
    'depends': ['product', 'resale_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/brand_attribute.xml',
        'views/product_template_views.xml',
        'views/condition_text_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
}
