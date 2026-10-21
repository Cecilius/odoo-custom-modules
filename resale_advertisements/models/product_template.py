from odoo import _, api, fields, models
from odoo.exceptions import UserError
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
    listing_platform_ids = fields.Many2many(
        'resale.platform',
        string='Listed on',
        compute='_compute_listing_platform_ids',
        store=True,
        help='Platforms where this product currently has an advertisement.',
    )
    new_listing_url = fields.Char(
        string='Paste Ad Link',
        help='Paste an eBay, Wallapop or Vinted advertisement link and click Add.',
    )

    def action_add_listing(self):
        """Create or reuse a listing record from the pasted link and attach it."""
        self.ensure_one()
        url = (self.new_listing_url or '').strip()
        if not url:
            raise UserError(_('Paste an advertisement link first.'))
        listing = self.env['resale.listing'].create({'url': url})
        self.listing_ids |= listing
        self.new_listing_url = False
        return True

    def write(self, vals):
        """Delete advertisement records that lost their last product link."""
        if 'listing_ids' not in vals:
            return super().write(vals)
        old_listings = self.listing_ids
        result = super().write(vals)
        removed = old_listings - self.listing_ids
        if removed:
            self.env['resale.listing']._delete_orphans(removed)
        return result

    def unlink(self):
        """Remove advertisements that only the deleted products referenced."""
        linked_listings = self.listing_ids
        result = super().unlink()
        if linked_listings:
            self.env['resale.listing']._delete_orphans(linked_listings)
        return result

    @api.depends('listing_ids.platform_id')
    def _compute_listing_platform_ids(self):
        for record in self:
            record.listing_platform_ids = record.listing_ids.mapped('platform_id')

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
