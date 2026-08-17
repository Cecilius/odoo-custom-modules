# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    resale_item_ids = fields.One2many('resale.item', 'product_id', string='Resale Items')
    resale_brand_id = fields.Many2one('resale.brand', string='Resale Brand')
