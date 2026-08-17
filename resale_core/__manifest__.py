# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Resale Core',
    'version': '1.0.0',
    'category': 'Inventory/Resale',
    'summary': 'Acquisition batches, resale items, RFB labels, brands, categories, lifecycle',
    'author': 'Resale Project',
    'description': """
Resale Core
===========

Operational foundation for second-hand and salvaged electronics resale:

- Acquisition batches (one pallet / auction lot / purchase group).
- Resale items, one physical item per RFB.
- RFB label pool and category-scoped sequences.
- Controlled brand and category masters.
- Condition and warranty policy masters.
- Lifecycle state machine from intake to sold/scrapped.
""",
    'depends': [
        'base',
        'product',
        'stock',
        'purchase',
        'mail',
    ],
    'data': [
        'security/resale_groups.xml',
        'security/ir.model.access.csv',
        'data/resale_category_data.xml',
        'data/resale_brand_data.xml',
        'data/resale_condition_data.xml',
        'data/resale_warranty_policy_data.xml',
        'data/resale_sequence_data.xml',
        'views/resale_category_views.xml',
        'views/resale_brand_views.xml',
        'views/resale_rfb_label_views.xml',
        'views/resale_acquisition_batch_views.xml',
        'views/resale_item_views.xml',
        'views/resale_condition_views.xml',
        'views/resale_warranty_policy_views.xml',
        'views/resale_menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
