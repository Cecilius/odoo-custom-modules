# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            order.picking_ids.filtered(
                lambda picking: picking.picking_type_id.code == 'outgoing'
            ).action_assign()
            for line in order.order_line:
                product = line.product_id
                if not product or not product.rfb:
                    continue
                moves = order.picking_ids.move_ids.filtered(
                    lambda move: move.product_id == product
                )
                reserved = sum(moves.mapped('quantity'))
                if (
                    product.resale_state in ('ready', 'published')
                    and reserved >= line.product_uom_qty
                ):
                    product.write({'resale_state': 'reserved'})
        return res
