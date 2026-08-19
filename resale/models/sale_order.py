# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            for line in order.order_line:
                product = line.product_id
                if not product or not product.rfb:
                    continue
                if product.resale_state in ('ready', 'published'):
                    product.write({'resale_state': 'reserved'})
        return res
