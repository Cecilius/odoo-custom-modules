from odoo import fields, models


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
            sent_orders._move_helpdesk_ticket_stage('repair_helpdesk.stage_repair_quote_approval')
        return res

    def action_confirm(self):
        """When the customer confirms the quotation, move the ticket to awaiting item."""
        res = super().action_confirm()
        self._move_helpdesk_ticket_stage('repair_helpdesk.stage_repair_awaiting_item')
        return res
