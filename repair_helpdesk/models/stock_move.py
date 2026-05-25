from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        res = super().write(vals)
        for repair in self.mapped('repair_id'):
            if repair.helpdesk_ticket_id:
                repair._check_parts_and_update_ticket()
        return res
