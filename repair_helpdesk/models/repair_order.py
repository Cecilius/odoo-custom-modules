from odoo import fields, models, _


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

    def action_validate(self):
        res = super().action_validate()
        for r in self:
            if r.helpdesk_ticket_id:
                r.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_diagnostics')
        return res

    def action_repair_start(self):
        res = super().action_repair_start()
        for r in self:
            if r.helpdesk_ticket_id:
                if r.is_parts_available:
                    r.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_under_repair')
                else:
                    r.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_waiting_parts')
        return res

    def action_repair_end(self):
        res = super().action_repair_end()
        for r in self:
            if r.helpdesk_ticket_id:
                r.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_qc')
                self.env['repair_helpdesk.quality_control'].create({
                    'helpdesk_ticket_id': r.helpdesk_ticket_id.id,
                })
        return res

    def action_cancel(self):
        res = super().action_cancel()
        for r in self:
            if r.helpdesk_ticket_id:
                r.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_ready_for_repair')
        return res

    def _check_parts_and_update_ticket(self):
        for r in self:
            ticket = r.helpdesk_ticket_id
            if not ticket or not r.is_parts_available:
                continue
            waiting_stage = self.env.ref(
                'repair_helpdesk.stage_repair_waiting_parts',
                raise_if_not_found=False,
            )
            if waiting_stage and ticket.stage_id == waiting_stage:
                ticket._set_stage('repair_helpdesk.stage_repair_under_repair')
                ticket.message_post(
                    body=_('All parts for repair %s are now available. Moving to Under Repair.') % r.name
                )
