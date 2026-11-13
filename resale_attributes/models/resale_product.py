"""Restrict the shared resale-product brand to the configured Brand attribute."""

from odoo import fields, models


class ResaleProduct(models.Model):
    """Use the Brand attribute chosen in settings instead of matching by name."""
    _inherit = 'resale.product'

    brand_attribute_id = fields.Many2one(
        'product.attribute',
        string='Brand Attribute',
        compute='_compute_brand_attribute_id',
    )
    brand_value_id = fields.Many2one(
        domain="[('attribute_id', '=', brand_attribute_id)]",
    )

    def _compute_brand_attribute_id(self):
        attribute = self.env['product.template']._get_mapped_attribute('brand')
        for record in self:
            record.brand_attribute_id = attribute
