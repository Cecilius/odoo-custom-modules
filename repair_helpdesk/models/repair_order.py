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
