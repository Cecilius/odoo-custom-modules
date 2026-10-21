"""Platform advertisement links shared across resale product templates."""

from odoo import api, fields, models


class ResaleListing(models.Model):
    """One advertisement link on one sales platform, shared by many products."""
    _name = 'resale.listing'
    _table = 'resale_listing'
    _description = 'Resale Platform Advertisement'
    _order = 'platform_id, url, id'

    _url_unique = models.UniqueIndex(
        "USING btree (lower(btrim(url)))",
        'An advertisement with this URL already exists.',
    )

    platform_id = fields.Many2one(
        'resale.platform',
        string='Platform',
        ondelete='restrict',
        index=True,
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

    @api.depends('url', 'platform_id')
    def _compute_display_name(self):
        for record in self:
            prefix = record.platform_id.display_name or ''
            record.display_name = ' - '.join(part for part in (prefix, record.url) if part)

    @api.model_create_multi
    def create(self, vals_list):
        """Detect platform from the link, stamp the date, and reuse known URLs."""
        resolved = []
        fresh_vals = []
        for vals in vals_list:
            self._strip_url(vals)
            self._infer_platform(vals)
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
        self._strip_url(vals)
        return super().write(vals)

    @staticmethod
    def _strip_url(vals):
        if isinstance(vals.get('url'), str):
            vals['url'] = vals['url'].strip() or False

    def _infer_platform(self, vals):
        if vals.get('platform_id') or not isinstance(vals.get('url'), str):
            return
        vals['platform_id'] = self._detect_platform_id(vals['url'])

    def _detect_platform_id(self, url):
        lowered = url.lower()
        platforms = self.env['resale.platform'].search([], order='sequence, id')
        for platform in platforms:
            keyword = (platform.host_keyword or platform.name or '').lower().strip()
            if keyword and keyword in lowered:
                return platform.id
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
