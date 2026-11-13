{
    'name': 'Resale Base',
    'version': '19.0.1.1.0',
    'summary': 'Shared foundation and settings area for resale modules',
    'category': 'Inventory/Resale',
    'author': 'Reparero',
    'website': 'https://reparero.es',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/resale_security.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
}
