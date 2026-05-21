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
            raise UserError(_("You can only change the journal and simplified flag while the invoice is still in draft."))
    
    def action_set_simplified(self):
        self._ensure_draft_move()
        move = self.move_id
        if not move:
            return {"type": "ir.actions.act_window_close"}
        move.write({
            "journal_id": move.company_id.simplified_sales_journal_id.id,
            "l10n_es_is_simplified": True,
        })
        return {"type": "ir.actions.act_window_close"}
        #don't post automatically, just adjust the values and user need to repost.
        #return move.with_context(allow_invoice_exception=True).action_post()

    def action_set_full(self):
        self._ensure_draft_move()
        move = self.move_id
        if not move:
            return {"type": "ir.actions.act_window_close"}
        move.write({
            "journal_id": move.company_id.full_sales_journal_id.id,
            "l10n_es_is_simplified": False,
        })
        return {"type": "ir.actions.act_window_close"}
        #don't post automatically, just adjust the values and user need to repost.
        #return move.with_context(allow_invoice_exception=True).action_post()

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}