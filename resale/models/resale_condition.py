# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResaleCondition(models.Model):
    _name = 'resale.condition'
    _description = 'Resale Condition'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    operator_description = fields.Text(string='Operator Description')
    advertisement_text_es = fields.Text(string='Advertisement Text (Spanish)')
    advertisement_text_en = fields.Text(string='Advertisement Text (English)')
    invoice_text_es = fields.Text(string='Invoice Text (Spanish)')
    invoice_text_en = fields.Text(string='Invoice Text (English)')

    condition_factor = fields.Float(string='Condition Factor', default=1.0)
    warranty_policy_id = fields.Many2one('resale.warranty.policy', string='Default Warranty Policy')
    functional_warranty = fields.Boolean(string='Functional Warranty', default=True)
    is_for_parts = fields.Boolean(string='For Parts', default=False)

    _code_uniq = models.Constraint(
        'unique(code)',
        'Condition code must be unique.',
    )
