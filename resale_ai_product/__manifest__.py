{
    'name': 'Resale AI Product Research',
    'version': '19.0.1.0.1',
    'summary': 'Research and create resale products with configurable AI agents',
    'category': 'Inventory/Resale',
    'author': 'Reparero',
    'website': 'https://reparero.es',
    'license': 'LGPL-3',
    'depends': ['resale_product', 'resale_base', 'resale_attributes', 'resale_category_sequencer', 'resale_ai_base', 'ai_provider_catalog'],
    'data': ['security/ir.model.access.csv', 'views/res_config_settings_views.xml', 'views/resale_product_wizard_views.xml'],
    'installable': True,
    'application': True,
}
