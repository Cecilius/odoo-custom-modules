from odoo import _, fields, models
from odoo.exceptions import UserError


class SimplifiedInvoicePostWizard(models.TransientModel):
    _name = "simplified.invoice.post.wizard"
    _description = "Simplified Invoice Post Wizard"

    move_id = fields.Many2one("account.move", required=True, readonly=True)
    message = fields.Text(readonly=True)

    def _ensure_draft_move(self):
        self.ensure_one()
        if not self.move_id or self.move_id.state != "draft":
            raise UserError(_(
                "You can only change the journal and simplified flag while the invoice is still in draft."
            ))

    def _set_classification(self, simplified):
        """Align the journal and simplified flag; the user posts again afterwards."""
        self._ensure_draft_move()
        move = self.move_id
        company = move.company_id
        journal = company.simplified_sales_journal_id if simplified else company.full_sales_journal_id
        values = {"l10n_es_is_simplified": simplified}
        if journal:
            values["journal_id"] = journal.id
        move.write(values)
        return {"type": "ir.actions.act_window_close"}

    def action_set_simplified(self):
        return self._set_classification(True)

    def action_set_full(self):
        return self._set_classification(False)

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}
