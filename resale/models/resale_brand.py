# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResaleBrand(models.Model):
    _name = 'resale.brand'
    _description = 'Resale Brand'
    _order = 'name'

    name = fields.Char(string='Name', required=True, index=True)
    active = fields.Boolean(string='Active', default=True)
    website_visible = fields.Boolean(string='Visible on Website', default=True)
    is_fallback = fields.Boolean(string='Fallback Brand', default=False)
    aliases = fields.Text(string='Aliases')
    note = fields.Text(string='Note')
    product_ids = fields.One2many('product.product', 'resale_brand_id', string='Products')

    _name_uniq = models.Constraint(
        'unique(name)',
        'Brand name must be unique.',
    )
