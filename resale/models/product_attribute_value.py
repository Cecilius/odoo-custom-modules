# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


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
    resale_is_brand = fields.Boolean(string='Brand', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        values = super().create(vals_list)
        brand_attribute = self.env.ref(
            'resale.product_attribute_brand',
            raise_if_not_found=False,
        )
        if brand_attribute:
            values.filtered(
                lambda value: value.attribute_id == brand_attribute
            ).write({'resale_is_brand': True})
        return values

    def write(self, vals):
        result = super().write(vals)
        if 'attribute_id' in vals:
            brand_attribute = self.env.ref(
                'resale.product_attribute_brand',
                raise_if_not_found=False,
            )
            if brand_attribute:
                brand_values = self.filtered(
                    lambda value: value.attribute_id == brand_attribute
                )
                brand_values.write({'resale_is_brand': True})
                (self - brand_values).write({'resale_is_brand': False})
        return result

    @api.model
    def _ensure_brand_values_all(self):
        brand_attribute = self.env.ref(
            'resale.product_attribute_brand',
            raise_if_not_found=False,
        )
        if brand_attribute:
            self.search([('attribute_id', '=', brand_attribute.id)]).write({
                'resale_is_brand': True,
            })
