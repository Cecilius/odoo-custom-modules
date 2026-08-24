{
    'name': 'Resale Advertisements',
    'version': '19.0.1.1.0',
    'summary': 'Long and short listing descriptions with AI generation for resale products',
    'category': 'Inventory/Resale',
    'author': 'Resale Project',
    'license': 'LGPL-3',
    'depends': ['product', 'resale_base', 'resale_product', 'resale_product_tests', 'ai_provider_catalog'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/product_template_views.xml',
        'views/advertisement_generator_wizard_views.xml',
        'views/advertisement_short_generator_views.xml',
    ],
    'installable': True,
    'application': False,
}
