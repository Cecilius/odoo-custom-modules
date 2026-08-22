# -*- coding: utf-8 -*-
{
    'name': 'Product RFB Sequence by Category',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Generates RFB-XX-YYYYYY internal reference via button action.',
    'author': 'Reparero',
    'website': 'https://reparero.es',
    'license': 'LGPL-3',
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_category_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}