"""Platform advertisement links shared across resale product templates."""

from odoo import api, fields, models

PLATFORM_SELECTION = [
    ('ebay', 'eBay'),
    ('wallapop', 'Wallapop'),
    ('vinted', 'Vinted'),
]

STATUS_SELECTION = [
    ('draft', 'Draft'),
    ('listed', 'Listed'),
    ('sold', 'Sold'),
    ('removed', 'Removed'),
]


class ResaleListing(models.Model):
    """One advertisement on one sales platform, linked to many products."""
    _name = 'resale.listing'
    _table = 'resale_listing'
    _description = 'Resale Platform Advertisement'
    _order = 'platform, name, id'

    _url_unique = models.UniqueIndex(
        "USING btree (platform, lower(btrim(url)))",
        'An advertisement with this URL already exists on this platform.',
    )

    name = fields.Char(
        string='Ad Title',
        help='Optional title of the advertisement on the platform.',
    )
    platform = fields.Selection(
        PLATFORM_SELECTION,
        string='Platform',
        required=True,
    )
    url = fields.Char(
        string='Advertisement URL',
        required=True,
        help='Direct link to the advertisement on the platform.',
    )
    status = fields.Selection(
        STATUS_SELECTION,
        string='Status',
        required=True,
        default='listed',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        ondelete='restrict',
    )
    price = fields.Monetary(
        string='Ad Price',
        currency_field='currency_id',
    )
    date_listed = fields.Date(string='Listed On')
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

    @api.depends('name', 'url', 'platform')
    def _compute_display_name(self):
        platforms = dict(PLATFORM_SELECTION)
        for record in self:
            label = record.name or record.url or ''
            prefix = platforms.get(record.platform, '')
            record.display_name = ' - '.join(part for part in (prefix, label) if part)

    @api.model_create_multi
    def create(self, vals_list):
        """Normalize links and reuse the existing record for duplicate URLs."""
        resolved = []
        fresh_vals = []
        for vals in vals_list:
            self._normalize_values(vals)
            existing = False
            if vals.get('platform') and vals.get('url'):
                existing = self._find_existing(vals['platform'], vals['url'])
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

    def _find_existing(self, platform, url):
        return self.search([
            ('platform', '=', platform),
            ('url', '=ilike', url),
        ], limit=1)

    def action_open_products(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Products',
            'res_model': 'product.template',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', self.product_template_ids.ids)],
        }
