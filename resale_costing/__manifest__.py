# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Resale Costing',
    'version': '1.0.0',
    'category': 'Inventory/Resale',
    'summary': 'Batch cost components, proportional allocation, and locked costs',
    'author': 'Resale Project',
    'description': """
Resale Costing
==============

Cost management for second-hand and salvaged electronics acquisitions:

- Authoritative batch cost components.
- Proportional acquisition cost allocation by adjusted value.
- Cost locking controlled by managers.
- Accountable cost adjustments for locked items.
""",
    'depends': [
        'resale_core',
        'account',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/resale_acquisition_batch_views.xml',
        'views/resale_cost_component_views.xml',
        'views/resale_cost_adjustment_views.xml',
        'views/resale_menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
