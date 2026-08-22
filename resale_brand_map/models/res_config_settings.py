from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    brand_attribute_id = fields.Many2one(
        'product.attribute',
        string='Brand Attribute',
        config_parameter='resale_brand_map.brand_attribute_id',
        default=lambda self: self.env.ref(
            'resale_brand_map.product_attribute_brand',
            raise_if_not_found=False,
        ),
        domain=[('create_variant', '=', 'no_variant')],
        help='Attribute whose values are used as Brand on product templates.',
    )
