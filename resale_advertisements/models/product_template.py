from odoo import _, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    long_listing = fields.Html(
        string='Long Listing',
        sanitize_attributes=False,
        translate=True,
        help='Detailed listing description used on marketplaces and resale channels.',
    )
    short_listing = fields.Html(
        string='Short Listing',
        sanitize_attributes=False,
        translate=True,
        help='Concise listing description for resale channels.',
    )

    def action_generate_long_listing(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generate Long Listing'),
            'res_model': 'resale.advertisement.generator',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_template_id': self.id},
        }

    def action_generate_short_listing(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generate Short Listing'),
            'res_model': 'resale.advertisement.short_generator',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_template_id': self.id},
        }
