from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    resale_product_test_ids = fields.One2many(
        'resale.product.test',
        'product_template_id',
        string='Product Tests',
    )
