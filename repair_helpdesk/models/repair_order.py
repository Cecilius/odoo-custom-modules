from odoo import fields, models, _
import logging

_logger = logging.getLogger(__name__)


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
        return res

    def action_cancel(self):
        res = super().action_cancel()
        for r in self:
            if r.helpdesk_ticket_id:
                r.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_ready_for_repair')
        return res

    def write(self, vals):
        _logger.info("=== repair.write called ids=%s vals=%s", self.ids, vals)
        old_available = {}
        for r in self:
            self.env.cr.execute(
                "SELECT is_parts_available FROM repair_order WHERE id = %s",
                [r.id],
            )
            row = self.env.cr.fetchone()
            db_val = row and row[0]
            cache_val = r.is_parts_available
            old_available[r.id] = db_val
            _logger.info(
                "  repair %s: DB is_parts_available=%s, cache is_parts_available=%s",
                r.id, db_val, cache_val,
            )
        res = super().write(vals)
        for r in self:
            ticket = r.helpdesk_ticket_id
            if not ticket:
                _logger.info("  repair %s: no ticket, skip", r.id)
                continue
            _logger.info(
                "  repair %s: after write is_parts_available=%s, old=%s, ticket.stage_id=%s",
                r.id, r.is_parts_available, old_available.get(r.id), ticket.stage_id.id,
            )
            if r.is_parts_available and not old_available.get(r.id):
                waiting_stage = self.env.ref(
                    'repair_helpdesk.stage_repair_waiting_parts',
                    raise_if_not_found=False,
                )
                if waiting_stage and ticket.stage_id == waiting_stage:
                    _logger.info("  -> MATCH! Moving ticket to Under Repair")
                    ticket._set_stage('repair_helpdesk.stage_repair_under_repair')
                    ticket.message_post(
                        body=_('All parts for repair %s are now available. Moving to Under Repair.') % r.name
                    )
                else:
                    _logger.info(
                        "  -> waiting_stage=%s, ticket.stage_id=%s",
                        waiting_stage and waiting_stage.id,
                        ticket.stage_id.id,
                    )
            else:
                _logger.info(
                    "  -> no match: is_parts_available=%s, old=%s",
                    r.is_parts_available,
                    old_available.get(r.id),
                )
        return res
