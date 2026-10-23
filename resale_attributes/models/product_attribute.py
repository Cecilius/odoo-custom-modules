"""Per-attribute switch for describing values on sale and invoice lines."""

from odoo import fields, models


class ProductAttribute(models.Model):
    """Mark which no-variant attributes appear in document line descriptions."""
    _inherit = 'product.attribute'

    resale_show_on_lines = fields.Boolean(
        string='Show on sale & invoice lines',
        default=False,
        help='Assigned values of this non-variant attribute are described in '
             'sale order and invoice line descriptions.',
    )
