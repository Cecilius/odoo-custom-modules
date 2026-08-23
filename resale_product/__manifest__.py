{
    'name': 'Resale Products',
    'version': '19.0.2.0.0',
    'summary': 'Manage shared resale product information and compliance',
    'category': 'Inventory/Resale',
    'author': 'Resale Project',
    'license': 'LGPL-3',
    'depends': ['product', 'contacts', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/resale_product_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': True,
}
