{
    'name': 'Resale AI Manufacturer',
    'version': '19.0.1.0.0',
    'summary': 'AI-assisted GPSR compliance: manufacturer, EU responsible person, CE and safety records',
    'category': 'Inventory/Resale',
    'author': 'Resale Project',
    'license': 'LGPL-3',
    'depends': ['resale_base', 'resale_product', 'ai_provider_catalog'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/resale_product_views.xml',
        'views/resale_ai_manufacturer_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
