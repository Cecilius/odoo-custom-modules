{
    'name': 'Resale Product Tests',
    'version': '19.0.1.0.0',
    'summary': 'Record product testing results and notes',
    'category': 'Inventory/Resale',
    'author': 'Resale Project',
    'license': 'LGPL-3',
    'depends': ['product', 'resale_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/resale_product_test_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
}
