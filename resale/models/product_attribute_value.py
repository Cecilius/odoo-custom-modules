# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    resale_condition_id = fields.Many2one(
        'resale.condition',
        string='Resale Condition Grade',
        copy=False,
    )
    resale_warranty_policy_id = fields.Many2one(
        'resale.warranty.policy',
        string='Warranty Policy',
        copy=False,
    )
    resale_condition_factor = fields.Float(
        string='Condition Factor',
        default=1.0,
        copy=False,
    )
    resale_is_for_parts = fields.Boolean(string='For Spare Parts', copy=False)
    resale_is_condition_grade = fields.Boolean(string='Condition Grade', copy=False)
