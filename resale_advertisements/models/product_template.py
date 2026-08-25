from odoo import _, api, fields, models
from odoo.tools.mail import html2plaintext


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
    long_listing_copy = fields.Text(
        string='Long Listing (copy)',
        compute='_compute_long_listing_copy',
        help='Combined long listing, condition listing text and internal reference for copy/paste.',
    )
    short_listing_copy = fields.Text(
        string='Short Listing (copy)',
        compute='_compute_short_listing_copy',
        help='Combined short listing, condition listing text and internal reference for copy/paste.',
    )

    @api.depends('long_listing', 'condition_listing_text', 'default_code')
    def _compute_long_listing_copy(self):
        for record in self:
            parts = [
                html2plaintext(record.long_listing or '') if record.long_listing else '',
                html2plaintext(record.condition_listing_text or '') if record.condition_listing_text else '',
                record.default_code or '',
            ]
            record.long_listing_copy = '\n'.join(part for part in parts if part)

    @api.depends('short_listing', 'condition_listing_text', 'default_code')
    def _compute_short_listing_copy(self):
        for record in self:
            parts = [
                html2plaintext(record.short_listing or '') if record.short_listing else '',
                html2plaintext(record.condition_listing_text or '') if record.condition_listing_text else '',
                record.default_code or '',
            ]
            record.short_listing_copy = '\n'.join(part for part in parts if part)

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
