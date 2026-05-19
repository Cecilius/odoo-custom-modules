{
    'name': 'Spain Simplified Invoice Workflow',
    'version': '19.0.2.0.0',
    'summary': 'Manual review workflow reusing Spanish localization simplified invoice logic',
    'category': 'Accounting/Accounting',
    'author': 'Perplexity',
    'license': 'LGPL-3',
    'depends': ['account', 'sale', 'website_sale', 'l10n_es'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml'
    ],
    'installable': True,
    'application': False,
}
