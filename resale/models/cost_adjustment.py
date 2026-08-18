# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class CostAdjustment(models.Model):
    _name = 'resale.cost.adjustment'
    _inherit = ['mail.thread']
    _description = 'Cost Adjustment'
    _order = 'date desc'

    product_id = fields.Many2one('product.product', string='Item', required=True,
                                 ondelete='restrict')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    amount = fields.Monetary(string='Adjustment Amount', required=True,
                             currency_field='currency_id')
    currency_id = fields.Many2one('res.currency',
                                  default=lambda self: self.env.company.currency_id)
    reason = fields.Text(string='Reason', required=True)
    user_id = fields.Many2one('res.users', string='User',
                              default=lambda self: self.env.user)

    @api.model_create_multi
    def create(self, vals_list):
        adjustments = super().create(vals_list)
        for adjustment in adjustments:
            if adjustment.product_id:
                adjustment.product_id.with_context(resale_lock_cost=True).write({
                    'acquisition_cost': adjustment.product_id.acquisition_cost + adjustment.amount,
                })
        return adjustments
