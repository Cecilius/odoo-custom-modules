# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AcquisitionBatch(models.Model):
    _name = 'resale.acquisition.batch'
    _inherit = ['mail.thread']
    _description = 'Acquisition Batch'
    _order = 'name desc'

    name = fields.Char(string='Reference', required=True, copy=False, default='New')
    partner_id = fields.Many2one('res.partner', string='Supplier', required=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    source_ref = fields.Char(string='Auction / Source Reference')
    acquisition_date = fields.Date(string='Acquisition Date', default=fields.Date.context_today)
    expected_arrival = fields.Date(string='Expected Arrival')
    received_date = fields.Date(string='Received Date')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    tax_regime = fields.Selection([
        ('vat', 'Regular VAT'),
        ('rebu', 'REBU'),
        ('other', 'Other / Manual review'),
    ], string='Tax Regime', default='vat', required=True)

    expected_items = fields.Integer(string='Expected Items', default=0)
    received_items = fields.Integer(
        string='Received Items',
        compute='_compute_item_counts', store=True,
    )
    item_ids = fields.One2many('resale.item', 'batch_id', string='Items')

    state = fields.Selection([
        ('ordered', 'Ordered'),
        ('awaiting', 'Awaiting Receipt'),
        ('received', 'Received / Sorting'),
        ('allocating', 'Allocating'),
        ('locked', 'Costs Locked'),
        ('done', 'Done'),
    ], string='Status', default='ordered', tracking=True)

    @api.depends('item_ids', 'item_ids.batch_id')
    def _compute_item_counts(self):
        for batch in self:
            batch.received_items = len(batch.item_ids)
