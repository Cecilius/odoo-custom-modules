# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class WarrantyPolicy(models.Model):
    _name = 'resale.warranty.policy'
    _description = 'Warranty Policy'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    duration_months = fields.Integer(string='Duration (months)')
    has_functional_warranty = fields.Boolean(string='Functional Warranty', default=True)
    invoice_text_es = fields.Text(string='Invoice Text (Spanish)')
    invoice_text_en = fields.Text(string='Invoice Text (English)')
    sequence = fields.Integer(string='Sequence', default=10)

    _code_uniq = models.Constraint(
        'unique(code)',
        'Warranty policy code must be unique.',
    )
