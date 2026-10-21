"""Platform advertisement links shared across resale product templates."""

from odoo import api, fields, models

PLATFORM_SELECTION = [
    ('ebay', 'eBay'),
    ('wallapop', 'Wallapop'),
    ('vinted', 'Vinted'),
]

PLATFORM_HOSTS = {
    'ebay': 'ebay',
    'wallapop': 'wallapop',
    'vinted': 'vinted',
}


class ResaleListing(models.Model):
    """One advertisement link on one sales platform, shared by many products."""
    _name = 'resale.listing'
    _table = 'resale_listing'
    _description = 'Resale Platform Advertisement'
    _order = 'platform, url, id'

    _url_unique = models.UniqueIndex(
        "USING btree (platform, lower(btrim(url)))",
        'An advertisement with this URL already exists.',
    )

    platform = fields.Selection(
        PLATFORM_SELECTION,
        string='Platform',
        help='Detected automatically from the link; can be corrected manually.',
    )
    url = fields.Char(
        string='Advertisement URL',
        required=True,
        help='Direct link to the advertisement on the platform.',
    )
    date_listed = fields.Date(
        string='Listed On',
        default=fields.Date.context_today,
    )
    product_template_ids = fields.Many2many(
        'product.template',
        'product_template_resale_listing_rel',
        'listing_id',
        'product_template_id',
        string='Products',
        help='Product templates covered by this advertisement (combined ads share one link).',
    )
    product_count = fields.Integer(
        string='Products',
        compute='_compute_product_count',
    )

    @api.depends('product_template_ids')
    def _compute_product_count(self):
        for record in self:
            record.product_count = len(record.product_template_ids)

    @api.depends('url', 'platform')
    def _compute_display_name(self):
        platforms = dict(PLATFORM_SELECTION)
        for record in self:
            prefix = platforms.get(record.platform, '')
            label = record.url or ''
            record.display_name = ' - '.join(part for part in (prefix, label) if part)

    @api.model_create_multi
    def create(self, vals_list):
        """Detect platform from the link, stamp the date, and reuse known URLs."""
        resolved = []
        fresh_vals = []
        for vals in vals_list:
            self._normalize_values(vals)
            existing = self._find_existing(vals.get('url')) if vals.get('url') else False
            resolved.append(existing)
            if not existing:
                fresh_vals.append(vals)
        new_records = super().create(fresh_vals) if fresh_vals else self.browse()
        new_ids = iter(new_records.ids)
        return self.browse([
            record.id if record else next(new_ids)
            for record in resolved
        ])

    def write(self, vals):
        """Normalize links on updates so deduplication stays consistent."""
        self._normalize_values(vals)
        return super().write(vals)

    @staticmethod
    def _normalize_values(vals):
        if isinstance(vals.get('url'), str):
            vals['url'] = vals['url'].strip() or False
        if not vals.get('platform') and isinstance(vals.get('url'), str):
            vals['platform'] = ResaleListing._infer_platform(vals['url'])

    @staticmethod
    def _infer_platform(url):
        lowered = url.lower()
        for platform, needle in PLATFORM_HOSTS.items():
            if needle in lowered:
                return platform
        return False

    def _find_existing(self, url):
        return self.search([
            ('url', '=ilike', url),
        ], limit=1)

    @api.model
    def _delete_orphans(self, listings):
        """Remove advertisement records that no longer reference any product."""
        orphans = listings.filtered(lambda listing: not listing.product_template_ids)
        if orphans:
            orphans.unlink()

    def action_open_products(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Products',
            'res_model': 'product.template',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', self.product_template_ids.ids)],
        }
