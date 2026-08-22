from odoo import fields, models


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
