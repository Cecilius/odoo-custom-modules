from odoo import fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Reverse link to the originating helpdesk ticket.
    # This enables smart buttons and stage automation from the sales document.
    helpdesk_ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string='Helpdesk Ticket',
        copy=False,
        index=True,
    )

    def create(self, vals_list):
        ticket_id = self.env.context.get('repair_helpdesk_ticket_id')
        if ticket_id:
            for vals in vals_list if isinstance(vals_list, list) else [vals_list]:
                if not vals.get('helpdesk_ticket_id'):
                    vals['helpdesk_ticket_id'] = ticket_id
        return super().create(vals_list)

    def action_create_invoice(self):
        if not self.env.context.get('repair_helpdesk_force_invoice'):
            for order in self:
                ticket = order.helpdesk_ticket_id
                if not ticket:
                    continue
                finished_stage = self.env.ref(
                    'repair_helpdesk.stage_repair_finished',
                    raise_if_not_found=False,
                )
                if finished_stage and ticket.stage_id.id < finished_stage.id:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Confirm Invoice'),
                        'res_model': 'repair_helpdesk.invoice_confirm.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {'default_sale_order_id': order.id},
                    }
        return super().action_create_invoice()

    def _move_helpdesk_ticket_stage(self, xmlid):
        """Move the linked helpdesk ticket to a specific workflow stage."""
        for order in self:
            ticket = order.helpdesk_ticket_id
            if not ticket:
                continue
            stage = self.env.ref(xmlid, raise_if_not_found=False)
            if stage:
                ticket.stage_id = stage.id

    def message_post(self, **kwargs):
        res = super().message_post(**kwargs)
        if self.env.context.get('mark_so_as_sent'):
            sent_orders = self.filtered(lambda o: o.state == 'sent')
            for order in sent_orders:
                ticket = order.helpdesk_ticket_id
                if not ticket:
                    continue
                has_prior = ticket.sale_order_ids.filtered(lambda so: so.id != order.id)
                stage_xmlid = (
                    'repair_helpdesk.stage_repair_revised_approval'
                    if has_prior
                    else 'repair_helpdesk.stage_repair_quote_approval'
                )
                order._move_helpdesk_ticket_stage(stage_xmlid)
        return res

    def action_confirm(self):
        """When the customer confirms the quotation, move the ticket.

        If this is a revised quotation, old quotations are cancelled first.
        """
        res = super().action_confirm()
        for order in self:
            ticket = order.helpdesk_ticket_id
            if not ticket:
                continue
            prior = ticket.sale_order_ids.filtered(lambda so: so.id != order.id and so.state != 'cancel')
            if prior:
                prior.action_cancel()
            stage_xmlid = (
                'repair_helpdesk.stage_repair_ready_for_repair'
                if prior
                else 'repair_helpdesk.stage_repair_awaiting_item'
            )
            order._move_helpdesk_ticket_stage(stage_xmlid)
        return res
