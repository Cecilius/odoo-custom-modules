{
    'name': 'Resale Sale Documents',
    'version': '19.0.1.0.0',
    'summary': 'Describe selected product attributes and second-hand status on sale and invoice lines',
    'category': 'Inventory/Resale',
    'author': 'Resale Project',
    'license': 'LGPL-3',
    'depends': ['resale_attributes', 'sale', 'account'],
    'data': [
        'views/product_attribute_views.xml',
        'views/condition_text_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
}
