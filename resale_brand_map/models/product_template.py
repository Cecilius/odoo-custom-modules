from odoo import api, fields, models, Command


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _get_brand_attribute(self):
        configured_id = self.env['ir.config_parameter'].sudo().get_param(
            'resale_brand_map.brand_attribute_id'
        )
        attribute = self.env['product.attribute'].browse(int(configured_id)).exists() \
            if configured_id and configured_id.isdigit() else self.env['product.attribute']
        return attribute or self.env.ref(
            'resale_brand_map.product_attribute_brand',
            raise_if_not_found=False,
        )

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
        self.brand_attribute_id = self._get_brand_attribute()

    @api.depends('attribute_line_ids.value_ids')
    def _compute_brand_value_id(self):
        for template in self:
            attribute = template._get_brand_attribute()
            line = template.attribute_line_ids.filtered(
                lambda item: attribute and item.attribute_id == attribute
            )[:1]
            template.brand_value_id = line.value_ids[:1] if line else False

    def _inverse_brand_value_id(self):
        attribute = self._get_brand_attribute()
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
