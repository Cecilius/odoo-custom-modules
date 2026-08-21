{
    'name': 'AI Provider Catalog',
    'version': '19.0.1.0.0',
    'summary': 'Shared dynamic model selection for Odoo AI providers',
    'category': 'Hidden',
    'author': 'Reparero',
    'license': 'LGPL-3',
    'depends': ['ai_app'],
    'data': ['views/ai_agent_views.xml'],
    'assets': {
        'web.assets_backend': [
            'ai_provider_catalog/static/src/model_approval_reload.js',
        ],
    },
    'installable': True,
    'application': False,
}
