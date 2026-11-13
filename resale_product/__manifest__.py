{
    'name': 'Resale Products',
    'version': '19.0.2.0.1',
    'summary': 'Manage shared resale product information and compliance',
    'category': 'Inventory/Resale',
    'author': 'Reparero',
    'website': 'https://reparero.es',
    'license': 'LGPL-3',
    'depends': ['resale_base', 'product', 'contacts', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/resale_product_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': True,
}
