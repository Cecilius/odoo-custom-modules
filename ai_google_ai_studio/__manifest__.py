{
    'name': 'AI Google AI Studio Provider',
    'version': '19.0.1.0.0',
    'summary': 'Dynamic Google Gemini AI Studio models for Odoo AI',
    'category': 'Hidden',
    'author': 'Reparero',
    'license': 'LGPL-3',
    'depends': ['ai_provider_catalog'],
    'data': [
        'security/ir.model.access.csv',
        'views/google_model_views.xml',
        'views/google_model_menus.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
}
