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
    )
    tested_by_id = fields.Many2one(
        'res.users',
        string='Tested By',
        required=True,
        default=lambda self: self.env.user,
        ondelete='restrict',
    )
    result = fields.Selection(
        [
            ('no_issue', 'No Issue Found'),
            ('issues_found', 'Issues Found'),
            ('not_working', 'Not Working'),
            ('needs_repair', 'Needs Repair'),
        ],
        string='Result',
        required=True,
    )
    notes = fields.Text(string='Notes')
