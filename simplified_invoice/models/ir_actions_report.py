from odoo import _, models
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        data = data or {}
        is_proforma = data.get("proforma") or self.env.context.get("proforma_invoice")
        if is_proforma and self._is_invoice_report(report_ref):
            invoices = self.env["account.move"].browse(res_ids or [])
            if any(invoice.l10n_es_is_simplified for invoice in invoices):
                raise UserError(
                    _("Simplified invoices cannot be issued as proforma invoices.")
                )

        return super()._pre_render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
