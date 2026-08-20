# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_cancel(self):
        res = super().action_cancel()
        products = self.order_line.mapped('product_id').filtered('rfb')
        active_moves = self.env['stock.move'].search([
            ('product_id', 'in', products.ids),
            ('picking_id.picking_type_id.code', '=', 'outgoing'),
            ('state', 'not in', ('cancel', 'done')),
        ])
        reserved_products = active_moves.mapped('product_id')
        for product in products - reserved_products:
            if product.resale_state == 'reserved':
                product.write({'resale_state': 'ready'})
        return res

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
