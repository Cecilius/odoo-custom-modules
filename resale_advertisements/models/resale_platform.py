"""Editable sales platforms used by resale advertisements."""

from odoo import api, fields, models


class ResalePlatform(models.Model):
    """A resale marketplace (eBay, Wallapop, Vinted, ...)."""
    _name = 'resale.platform'
    _table = 'resale_platform'
    _description = 'Resale Sales Platform'
    _order = 'sequence, name, id'

    _name_unique = models.UniqueIndex(
        "USING btree (lower(btrim(name)))",
        'A platform with this name already exists.',
    )

    name = fields.Char(string='Name', required=True, translate=True)
    host_keyword = fields.Char(
        string='URL Keyword',
        compute='_compute_host_keyword',
        store=True,
        readonly=False,
        help='Substring used to detect the platform from a pasted link, e.g. "ebay".',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)

    @api.depends('name')
    def _compute_host_keyword(self):
        for record in self:
            if not record.host_keyword:
                record.host_keyword = (record.name or '').lower().strip()
