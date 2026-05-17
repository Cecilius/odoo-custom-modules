from odoo import fields, models


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    helpdesk_ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string='Helpdesk Ticket',
        copy=False,
        index=True,
    )
