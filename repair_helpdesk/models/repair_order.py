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
        ctx = self.env.context
        if self.helpdesk_ticket_id:
            ctx = dict(ctx, repair_helpdesk_ticket_id=self.helpdesk_ticket_id.id)
        return super(RepairOrder, self.with_context(**ctx)).action_create_sale_order()
