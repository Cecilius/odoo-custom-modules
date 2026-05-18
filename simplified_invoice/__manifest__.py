{
    'name': 'Spain Simplified Invoice Automation',
    'version': '19.0.1.0.0',
    'summary': 'Auto-route simplified vs full invoices and require tax ID when needed',
    'category': 'Accounting/Accounting',
    'author': 'Reparero',
    'website': "https://reparero.es",
    'license': 'LGPL-3',
    'depends': ['account', 'sale', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
}
