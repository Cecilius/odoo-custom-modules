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
