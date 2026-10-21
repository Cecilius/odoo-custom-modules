from odoo import _, api, fields, models
from odoo.tools.mail import html2plaintext


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    short_listing = fields.Html(
        string='Short Listing',
        sanitize_attributes=False,
        help='Concise listing description for resale channels (single language).',
    )
    short_listing_copy = fields.Text(
        string='Short Listing (copy)',
        compute='_compute_short_listing_copy',
        help='Combined short listing, condition listing text and internal reference for copy/paste.',
    )
    listing_ids = fields.Many2many(
        'resale.listing',
        'product_template_resale_listing_rel',
        'product_template_id',
        'listing_id',
        string='Platform Advertisements',
        help='Advertisements on external platforms that include this product.',
    )
    listing_count = fields.Integer(
        string='Advertisement Count',
        compute='_compute_listing_flags',
    )
    listed_on_ebay = fields.Boolean(
        string='Listed on eBay',
        compute='_compute_listing_flags',
        store=True,
    )
    listed_on_wallapop = fields.Boolean(
        string='Listed on Wallapop',
        compute='_compute_listing_flags',
        store=True,
    )
    listed_on_vinted = fields.Boolean(
        string='Listed on Vinted',
        compute='_compute_listing_flags',
        store=True,
    )

    @api.depends('listing_ids.platform')
    def _compute_listing_flags(self):
        for record in self:
            platforms = set(record.listing_ids.mapped('platform'))
            record.listed_on_ebay = 'ebay' in platforms
            record.listed_on_wallapop = 'wallapop' in platforms
            record.listed_on_vinted = 'vinted' in platforms
            record.listing_count = len(record.listing_ids)

    @api.depends('short_listing', 'condition_listing_text', 'default_code')
    def _compute_short_listing_copy(self):
        for record in self:
            parts = [
                html2plaintext(record.short_listing or '') if record.short_listing else '',
                html2plaintext(record.condition_listing_text or '') if record.condition_listing_text else '',
                record.default_code or '',
            ]
            record.short_listing_copy = '\n\n'.join(part for part in parts if part)

    def action_generate_description(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generate Description'),
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

    def action_translate_description(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Translate Description'),
            'res_model': 'resale.advertisement.translator',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_template_id': self.id},
        }
