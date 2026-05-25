from odoo import fields, models


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    # Reverse link to the originating helpdesk ticket.
    # This keeps repairs and support requests connected in both directions.
    helpdesk_ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string='Helpdesk Ticket',
        copy=False,
        index=True,
    )

    def action_create_sale_order(self):
        self.ensure_one()
        ctx = self.env.context
        if self.helpdesk_ticket_id:
            ctx = dict(ctx, repair_helpdesk_ticket_id=self.helpdesk_ticket_id.id)
        return super(RepairOrder, self.with_context(**ctx)).action_create_sale_order()

    def action_repair_start(self):
        res = super().action_repair_start()
        for r in self:
            if r.helpdesk_ticket_id:
                r.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_under_repair')
        return res

    def action_repair_end(self):
        res = super().action_repair_end()
        for r in self:
            if r.helpdesk_ticket_id:
                r.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_qc')
        return res

    def action_cancel(self):
        res = super().action_cancel()
        for r in self:
            if r.helpdesk_ticket_id:
                r.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_ready_for_repair')
        return res
