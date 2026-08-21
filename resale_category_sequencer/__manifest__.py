# -*- coding: utf-8 -*-
{
    'name': 'Product RFB Sequence by Category',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Generates RFB-XX-YYYYYY internal references based on 2-digit category codes.',
    'author': 'Reparero',
    'website': 'https://reparero.es',
    'license': 'LGPL-3',
    'depends': ['product', 'stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_category_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'resale_category_sequencer/static/src/js/product_form_controller.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
