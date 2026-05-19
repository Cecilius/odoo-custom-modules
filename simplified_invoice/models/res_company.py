from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    simplified_sales_journal_id = fields.Many2one(
        "account.journal",
        string="Simplified Sales Journal",
        domain="[('type', '=', 'sale')]",
        help="Used when a Spanish invoice is detected as simplified by l10n_es_is_simplified.",
    )
    full_sales_journal_id = fields.Many2one(
        "account.journal",
        string="Full Sales Journal",
        domain="[('type', '=', 'sale')]",
        help="Used as the default sales journal for non-simplified invoices.",
    )
