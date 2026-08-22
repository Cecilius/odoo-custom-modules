{
    'name': 'Resale AI Intake',
    'version': '19.0.1.0.0',
    'summary': 'Configurable native Odoo AI intake for resale items',
    'category': 'Inventory/Resale',
    'author': 'Resale Project',
    'license': 'LGPL-3',
    'depends': [
        'resale',
        'ai_google_ai_studio',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/resale_ai_configuration_data.xml',
        'views/resale_ai_configuration_views.xml',
        'views/resale_ai_intake_views.xml',
        'views/resale_ai_lookup_views.xml',
        'views/resale_ai_research_views.xml',
        'views/acquisition_batch_views.xml',
        'views/resale_ai_menus.xml',
    ],
    'installable': True,
    'application': False,
}
