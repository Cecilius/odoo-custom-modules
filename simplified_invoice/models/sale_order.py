from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    invoice_review_state = fields.Selection([
        ('pending', 'Pending review'),
        ('approved', 'Approved'),
    ], default='pending', string='Invoice Review State', copy=False)
