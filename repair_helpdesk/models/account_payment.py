from odoo import fields, models, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        res = super().action_post()
        for pay in self:
            for inv in pay.reconciled_invoice_ids:
                ticket = inv._get_helpdesk_ticket()
                if not ticket:
                    continue
                ready_stage = self.env.ref('repair_helpdesk.stage_repair_ready_return', raise_if_not_found=False)
                payment_stage = self.env.ref('repair_helpdesk.stage_repair_payment', raise_if_not_found=False)
                if payment_stage and ready_stage and ticket.stage_id == payment_stage:
                    ticket._set_stage('repair_helpdesk.stage_repair_ready_return')
                    ticket.message_post(
                        subject=_('Payment received'),
                        body=_('Payment for invoice %s received. Ready for shipment.') % inv.name,
                        body_is_html=True,
                        message_type='comment',
                    )
        return res
