{
    'name': 'Spain Simplified Invoice Workflow',
    'version': '19.0.4.0.0',
    'summary': 'Manual review workflow reusing Spanish localization simplified invoice logic',
    'category': 'Accounting/Accounting',
    'author': 'Reparero',
    'license': 'LGPL-3',
    'depends': ['account', 'sale', 'website_sale', 'l10n_es'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/invoice_wizard_views.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'application': False,
}
