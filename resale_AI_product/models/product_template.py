from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    reference_retail_price = fields.Monetary(string='Reference Retail Price', currency_field='currency_id')
    launch_year = fields.Integer(string='Product Launch Year')
