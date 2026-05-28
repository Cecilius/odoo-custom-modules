from odoo import _, api, fields, models


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        seen = set()
        for r in records:
            for line in (r.debit_move_id, r.credit_move_id):
                inv = line.move_id
                if inv.move_type not in ('out_invoice', 'out_refund'):
                    continue
                if inv.id in seen:
                    continue
                seen.add(inv.id)
                if inv.payment_state == 'paid':
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
        return records
