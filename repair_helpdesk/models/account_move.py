from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_helpdesk_ticket(self):
        """Walk invoice lines to find the linked helpdesk ticket."""
        for line in self.invoice_line_ids:
            for sol in line.sale_line_ids:
                if sol.order_id.helpdesk_ticket_id:
                    return sol.order_id.helpdesk_ticket_id
        return self.env['helpdesk.ticket']

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.move_type in ('out_refund', 'in_refund'):
                continue
            ticket = move._get_helpdesk_ticket()
            if not ticket:
                continue
            payment_stage = self.env.ref('repair_helpdesk.stage_repair_payment', raise_if_not_found=False)
            if payment_stage and ticket.stage_id.id < payment_stage.id:
                ticket._set_stage('repair_helpdesk.stage_repair_payment')
                ticket.message_post(
                    subject=_('Invoice posted'),
                    body=_('Invoice %s posted. Ticket moved to Waiting for Payment.') % move.name,
                    body_is_html=True,
                    message_type='comment',
                )
        return res

    def write(self, vals):
        old_payment = {m.id: m.payment_state for m in self if m.payment_state != 'paid'}
        res = super().write(vals)
        for move in self:
            if move.move_type in ('out_refund', 'in_refund'):
                continue
            if move.id not in old_payment:
                continue
            if vals.get('payment_state') and move.payment_state == 'paid' and old_payment[move.id] != 'paid':
                ticket = move._get_helpdesk_ticket()
                if not ticket:
                    continue
                ready_stage = self.env.ref('repair_helpdesk.stage_repair_ready_return', raise_if_not_found=False)
                payment_stage = self.env.ref('repair_helpdesk.stage_repair_payment', raise_if_not_found=False)
                if payment_stage and ready_stage and ticket.stage_id == payment_stage:
                    ticket._set_stage('repair_helpdesk.stage_repair_ready_return')
                    ticket.message_post(
                        subject=_('Payment received'),
                        body=_('Payment for invoice %s received. Ready for shipment.') % move.name,
                        body_is_html=True,
                        message_type='comment',
                    )
        return res
