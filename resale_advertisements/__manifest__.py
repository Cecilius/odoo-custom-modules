{
    'name': 'Resale Advertisements',
    'version': '19.0.1.1.1',
    'summary': 'Product descriptions and short listings with AI generation for resale products',
    'category': 'Inventory/Resale',
    'author': 'Resale Project',
    'license': 'LGPL-3',
    'depends': ['product', 'resale_base', 'resale_product', 'resale_product_tests', 'resale_attributes', 'ai_provider_catalog', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/product_template_views.xml',
        'views/advertisement_generator_wizard_views.xml',
        'views/advertisement_short_generator_views.xml',
        'views/advertisement_translator_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
