from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    simplified_invoice_threshold = fields.Monetary(
        string='Simplified Invoice Threshold',
        currency_field='currency_id',
        default=400.0,
        help='Business rule threshold. Spanish law may allow additional simplified invoice cases up to 3000 EUR depending on activity.'
    )
    simplified_sales_journal_id = fields.Many2one(
        'account.journal',
        string='Simplified Sales Journal',
        domain="[('type', '=', 'sale')]",
    )
    require_tax_id_for_full_invoice = fields.Boolean(
        string='Require customer tax ID for full invoice',
        default=True,
    )
