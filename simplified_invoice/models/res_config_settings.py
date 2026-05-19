from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    simplified_sales_journal_id = fields.Many2one(
        related="company_id.simplified_sales_journal_id",
        readonly=False,
    )
    full_sales_journal_id = fields.Many2one(
        related="company_id.full_sales_journal_id",
        readonly=False,
    )
