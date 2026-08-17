# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Resale Inspection',
    'version': '1.0.0',
    'category': 'Inventory/Resale',
    'summary': 'Initial evaluation and detailed testing for resale items',
    'author': 'Resale Project',
    'description': """
Resale Inspection
=================

Inspection workflow for second-hand and salvaged electronics:

- Initial evaluation during intake (lightweight identification + basic test).
- Detailed test completion with disposition.
- Category-specific test instructions.
""",
    'depends': [
        'resale_core',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/resale_initial_evaluation_views.xml',
        'views/resale_detailed_test_views.xml',
        'views/resale_test_type_views.xml',
        'views/resale_menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
