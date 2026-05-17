from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    helpdesk_ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string='Helpdesk Ticket',
        copy=False,
        index=True,
    )
