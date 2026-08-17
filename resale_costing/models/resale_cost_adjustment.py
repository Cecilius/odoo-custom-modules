# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class CostAdjustment(models.Model):
    _name = 'resale.cost.adjustment'
    _inherit = ['mail.thread']
    _description = 'Cost Adjustment'
    _order = 'date desc'

    item_id = fields.Many2one('resale.item', string='Item', required=True,
                              ondelete='restrict')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    amount = fields.Monetary(string='Adjustment Amount', required=True,
                             currency_field='currency_id')
    currency_id = fields.Many2one('res.currency',
                                  default=lambda self: self.env.company.currency_id)
    reason = fields.Text(string='Reason', required=True)
    user_id = fields.Many2one('res.users', string='User',
                              default=lambda self: self.env.user)
