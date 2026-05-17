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

    def action_quotation_send(self):
        """When the quotation sending flow is triggered, move the ticket to approval.

        Note: in standard Odoo this method launches the send wizard. If you need the
        stage to change only after the email is really sent, a deeper mail wizard hook
        would be needed later.
        """
        res = super().action_quotation_send()
        self._move_helpdesk_ticket_stage('repair_helpdesk.stage_repair_quote_approval')
        return res

    def action_confirm(self):
        """When the customer confirms the quotation, move the ticket to awaiting item."""
        res = super().action_confirm()
        self._move_helpdesk_ticket_stage('repair_helpdesk.stage_repair_awaiting_item')
        return res
