# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Resale',
    'version': '2.1.0',
    'category': 'Inventory/Resale',
    'summary': 'Second-hand and salvaged electronics resale workflow',
    'author': 'Resale Project',
    'description': """
Resale
======

Simplified resale workflow for second-hand electronics:

- One product.product record per physical item (RFB as default_code/barcode).
- Acquisition batches with bill/credit-note cost sync.
- Inline initial evaluation on the item.
- Detailed test completion records.
- Proportional cost allocation and manager lock.
- Standard SO / invoice / delivery for sales.
- Minimal stock tracking (resale stock + scrap).
""",
    'depends': [
        'base',
        'product',
        'stock',
        'account',
        'sale_management',
        'mail',
    ],
    'data': [
        'security/resale_groups.xml',
        'security/ir.model.access.csv',
        'data/resale_user_data.xml',
        'data/stock_location_data.xml',
        'data/resale_sequence_data.xml',
        'data/resale_category_data.xml',
        'data/resale_brand_data.xml',
        'data/resale_condition_data.xml',
        'data/resale_warranty_policy_data.xml',
        'views/product_category_views.xml',
        'views/resale_brand_views.xml',
        'views/resale_condition_views.xml',
        'views/resale_warranty_policy_views.xml',
        'views/resale_test_type_views.xml',
        'views/product_product_views.xml',
        'views/acquisition_batch_views.xml',
        'views/detailed_test_views.xml',
        'views/resale_menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
