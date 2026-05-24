from odoo import fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    helpdesk_ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string='Helpdesk Ticket',
        copy=False,
        index=True,
    )

    def _create_incoming_inspection(self):
        self.ensure_one()
        if self.picking_type_code != 'incoming' or not self.helpdesk_ticket_id:
            return
        if self.helpdesk_ticket_id.inspection_ids:
            return
        inspection = self.env['repair_helpdesk.incoming_inspection'].create({
            'helpdesk_ticket_id': self.helpdesk_ticket_id.id,
        })
        self.helpdesk_ticket_id.message_post(
            body=_('Incoming inspection %s created for shipment %s.') % (inspection.name, self.name)
        )

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals:
            done_pickings = self.filtered(lambda p: p.state == 'done' and p.helpdesk_ticket_id)
            for picking in done_pickings:
                if picking.picking_type_code == 'incoming':
                    picking._create_incoming_inspection()
                    picking.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_initial_inspection')
                elif picking.picking_type_code == 'outgoing':
                    picking.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_closed')
        return res

    def _action_done(self):
        res = super()._action_done()
        done_pickings = self.filtered(lambda p: p.state == 'done' and p.helpdesk_ticket_id)
        for picking in done_pickings:
            if picking.picking_type_code == 'incoming':
                picking._create_incoming_inspection()
                picking.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_initial_inspection')
            elif picking.picking_type_code == 'outgoing':
                picking.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_closed')
        return res
