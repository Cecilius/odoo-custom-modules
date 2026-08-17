# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResaleCategory(models.Model):
    _name = 'resale.category'
    _description = 'Resale Category'
    _order = 'code'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, size=2)
    active = fields.Boolean(string='Active', default=True)
    is_other = fields.Boolean(
        string='Other / Miscellaneous',
        help='Permanent fallback category for exceptional items.',
    )

    _code_uniq = models.Constraint(
        'unique(code)',
        'Category code must be unique.',
    )
