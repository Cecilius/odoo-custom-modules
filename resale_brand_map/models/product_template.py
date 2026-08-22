from odoo import api, fields, models, Command


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_attribute_id = fields.Many2one(
        'product.attribute',
        string='Brand Attribute',
        compute='_compute_brand_attribute_id',
    )
    brand_value_id = fields.Many2one(
        'product.attribute.value',
        string='Brand',
        compute='_compute_brand_value_id',
        inverse='_inverse_brand_value_id',
    )

    @api.depends('attribute_line_ids.value_ids')
    def _compute_brand_attribute_id(self):
        attribute = self.env.ref(
            'resale_brand_map.product_attribute_brand',
            raise_if_not_found=False,
        )
        self.brand_attribute_id = attribute

    @api.depends('attribute_line_ids.value_ids')
    def _compute_brand_value_id(self):
        attribute = self.env.ref(
            'resale_brand_map.product_attribute_brand',
            raise_if_not_found=False,
        )
        for template in self:
            line = template.attribute_line_ids.filtered(
                lambda item: attribute and item.attribute_id == attribute
            )[:1]
            template.brand_value_id = line.value_ids[:1] if line else False

    def _inverse_brand_value_id(self):
        attribute = self.env.ref(
            'resale_brand_map.product_attribute_brand',
            raise_if_not_found=False,
        )
        if not attribute:
            return
        for template in self:
            value = template.brand_value_id
            if value and value.attribute_id != attribute:
                continue
            line = template.attribute_line_ids.filtered(
                lambda item: item.attribute_id == attribute
            )[:1]
            if value:
                if line:
                    line.value_ids = [Command.set([value.id])]
                else:
                    self.env['product.template.attribute.line'].create({
                        'product_tmpl_id': template.id,
                        'attribute_id': attribute.id,
                        'value_ids': [Command.link(value.id)],
                    })
            elif line:
                line.unlink()
