from odoo import fields, models


class ResaleProductTest(models.Model):
    _name = 'resale.product.test'
    _description = 'Resale Product Test'
    _order = 'test_date desc, id desc'

    product_template_id = fields.Many2one(
        'product.template',
        string='Product',
        required=True,
        ondelete='cascade',
        index=True,
    )
    test_date = fields.Date(
        string='Test Date',
        required=True,
        default=fields.Date.context_today,
        readonly=True,
    )
    tested_by_id = fields.Many2one(
        'res.users',
        string='Tested By',
        required=True,
        default=lambda self: self.env.user,
        ondelete='restrict',
    )
    result_id = fields.Many2one(
        'resale.product.test.result',
        string='Result',
        required=True,
        ondelete='restrict',
        domain=[('active', '=', True)],
    )
    notes = fields.Text(string='Notes')
