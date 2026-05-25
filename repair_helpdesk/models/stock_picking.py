from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    helpdesk_ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string='Helpdesk Ticket',
        copy=False,
        index=True,
    )

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals:
            done_pickings = self.filtered(lambda p: p.state == 'done' and p.helpdesk_ticket_id)
            for picking in done_pickings:
                if picking.picking_type_code == 'incoming':
                    picking.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_initial_inspection')
                elif picking.picking_type_code == 'outgoing':
                    picking.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_closed')
        return res

    def _action_done(self):
        res = super()._action_done()
        done_pickings = self.filtered(lambda p: p.state == 'done' and p.helpdesk_ticket_id)
        for picking in done_pickings:
            if picking.picking_type_code == 'incoming':
                picking.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_initial_inspection')
            elif picking.picking_type_code == 'outgoing':
                picking.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_closed')
        return res
