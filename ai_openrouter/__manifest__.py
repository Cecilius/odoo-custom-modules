{
    'name': 'AI OpenRouter Provider',
    'version': '19.0.1.0.0',
    'summary': 'Use OpenRouter models in the Odoo AI application',
    'category': 'Hidden',
    'author': 'Reparero',
    'license': 'LGPL-3',
    'depends': ['ai_provider_catalog'],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_agent_views.xml',
        'views/openrouter_model_views.xml',
        'views/openrouter_model_menus.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
}
