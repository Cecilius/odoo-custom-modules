from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    brand_attribute_id = fields.Many2one(
        'product.attribute', string='Brand Attribute',
        config_parameter='resale_attributes.brand_attribute_id',
        default=lambda self: self.env.ref(
            'resale_attributes.product_attribute_brand', raise_if_not_found=False,
        ),
        domain=[('create_variant', '=', 'no_variant')],
    )
    condition_attribute_id = fields.Many2one(
        'product.attribute', string='Condition Attribute',
        config_parameter='resale_attributes.condition_attribute_id',
        default=lambda self: self.env.ref(
            'resale_attributes.product_attribute_condition', raise_if_not_found=False,
        ),
        domain=[('create_variant', '=', 'no_variant')],
    )
    box_attribute_id = fields.Many2one(
        'product.attribute', string='Box Attribute',
        config_parameter='resale_attributes.box_attribute_id',
        default=lambda self: self.env.ref(
            'resale_attributes.product_attribute_box', raise_if_not_found=False,
        ),
        domain=[('create_variant', '=', 'no_variant')],
    )
    warranty_attribute_id = fields.Many2one(
        'product.attribute', string='Warranty Attribute',
        config_parameter='resale_attributes.warranty_attribute_id',
        default=lambda self: self.env.ref(
            'resale_attributes.product_attribute_warranty', raise_if_not_found=False,
        ),
        domain=[('create_variant', '=', 'no_variant')],
    )

    @api.onchange('condition_attribute_id')
    def _onchange_condition_attribute_id(self):
        configured_id = self.env['ir.config_parameter'].sudo().get_param(
            'resale_attributes.condition_attribute_id'
        )
        old_id = int(configured_id) if configured_id and configured_id.isdigit() else False
        if not old_id or old_id == self.condition_attribute_id.id:
            return
        mapping_count = self.env['resale.condition.text'].search_count([
            ('condition_value_id.attribute_id', '=', old_id),
            ('active', '=', True),
        ])
        old_attribute = self.env['product.attribute'].browse(old_id)
        return {
            'warning': {
                'title': 'Condition attribute changed',
                'message': (
                    f'Changing from {old_attribute.display_name} to '
                    f'{self.condition_attribute_id.display_name} will archive '
                    f'{mapping_count} existing condition text mapping(s). '
                    'They will not be deleted.'
                ),
            }
        }

    def set_values(self):
        configured_id = self.env['ir.config_parameter'].sudo().get_param(
            'resale_attributes.condition_attribute_id'
        )
        old_id = int(configured_id) if configured_id and configured_id.isdigit() else False
        new_id = self.condition_attribute_id.id
        result = super().set_values()
        if old_id and new_id and old_id != new_id:
            self.env['resale.condition.text'].search([
                ('condition_value_id.attribute_id', '=', old_id),
                ('active', '=', True),
            ]).write({'active': False})
        return result
