from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_identification_type = fields.Selection([
        ('consumer', 'Consumer / Simplified allowed'),
        ('full', 'Full invoice required'),
    ], default='consumer', string='Invoice Identification Mode')
