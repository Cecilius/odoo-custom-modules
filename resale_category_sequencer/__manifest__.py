# -*- coding: utf-8 -*-
{
    'name': 'Product RFB Sequence by Category',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Generates RFB-XX-YYYYYY internal reference via button action.',
    'author': 'Reparero',
    'website': 'https://reparero.es',
    'license': 'LGPL-3',
    'depends': ['resale_base', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/rfb_sequence_server_actions.xml',
        'views/product_category_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
