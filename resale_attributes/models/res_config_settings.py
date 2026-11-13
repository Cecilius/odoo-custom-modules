"""Settings for selecting the product attributes used by resale workflows."""

from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    """Persist configurable attribute mappings and archive stale condition text."""
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
    default_warranty_value_id = fields.Many2one(
        'product.attribute.value', string='Default Warranty',
        config_parameter='resale_attributes.default_warranty_value_id',
        default_model='product.template',
        domain="[('attribute_id', '=', warranty_attribute_id)]",
    )

    @api.onchange('condition_attribute_id')
    def _onchange_condition_attribute_id(self):
        """Warn the operator before switching away from a mapped condition attribute."""
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
                'title': _('Condition attribute changed'),
                'message': _(
                    'Changing from %(old)s to %(new)s will archive %(count)s existing '
                    'condition text mapping(s). They will not be deleted.',
                    old=old_attribute.display_name,
                    new=self.condition_attribute_id.display_name,
                    count=mapping_count,
                ),
            }
        }

    def set_values(self):
        """Save settings and archive mappings tied to the previous condition attribute."""
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
