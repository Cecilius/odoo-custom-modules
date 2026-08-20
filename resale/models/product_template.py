# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, Command


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _ensure_default_condition_grade(self):
        attribute = self.env.ref(
            'resale.product_attribute_condition_grade',
            raise_if_not_found=False,
        )
        new_value = self.env.ref(
            'resale.product_attribute_value_condition_new',
            raise_if_not_found=False,
        )
        if not attribute or not new_value:
            return
        for template in self:
            line = template.attribute_line_ids.filtered(
                lambda item: item.attribute_id == attribute
            )[:1]
            if line:
                if not line.value_ids:
                    line.value_ids = [Command.link(new_value.id)]
            else:
                self.env['product.template.attribute.line'].create({
                    'product_tmpl_id': template.id,
                    'attribute_id': attribute.id,
                    'value_ids': [Command.link(new_value.id)],
                })

    @api.model
    def _ensure_default_condition_grade_all(self):
        self.search([])._ensure_default_condition_grade()

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        templates._ensure_default_condition_grade()
        service_policy = self.env.ref(
            'resale.warranty_service_3_months',
            raise_if_not_found=False,
        )
        goods_policy = self.env.ref(
            'resale.warranty_36_months',
            raise_if_not_found=False,
        )
        for template in templates:
            policy = service_policy if template.type == 'service' else goods_policy
            if policy:
                template.product_variant_ids.write({'warranty_policy_id': policy.id})
        return templates
