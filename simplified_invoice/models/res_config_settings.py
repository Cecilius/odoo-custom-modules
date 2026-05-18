from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    simplified_invoice_threshold = fields.Monetary(related='company_id.simplified_invoice_threshold', readonly=False)
    simplified_sales_journal_id = fields.Many2one(related='company_id.simplified_sales_journal_id', readonly=False)
    require_tax_id_for_full_invoice = fields.Boolean(related='company_id.require_tax_id_for_full_invoice', readonly=False)
