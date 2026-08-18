# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class TestType(models.Model):
    _name = 'resale.test.type'
    _description = 'Test Type'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True)
    category_id = fields.Many2one('product.category', string='Category')
    instructions = fields.Html(string='Procedure Instructions')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
