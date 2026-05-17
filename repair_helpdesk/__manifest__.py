{
    'name': 'Repair Helpdesk',
    'version': '19.0.1.0.0',
    'summary': 'Full workflow for electronics repair in Helpdesk',
    'category': 'Services/Helpdesk',
    'author': 'Reparero',
    'license': 'LGPL-3',
    'depends': ['helpdesk', 'sale_management', 'product', 'repair'],
    'data': [
        'security/ir.model.access.csv',
        'data/helpdesk_stage_data.xml',
        'data/helpdesk_team_data.xml',
        'data/product_data.xml',
        'views/helpdesk_team_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/sale_order_views.xml',
        'views/repair_order_views.xml'
    ],
    'installable': True,
    'application': False,
}
