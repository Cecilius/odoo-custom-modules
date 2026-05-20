from odoo import _, fields, models


class SimplifiedInvoicePostWizard(models.TransientModel):
    _name = "simplified.invoice.post.wizard"
    _description = "Simplified Invoice Post Wizard"

    move_id = fields.Many2one("account.move", required=True, readonly=True)
    message = fields.Text(readonly=True)

    def action_confirm_post(self):
        move = self.move_id
        if not move:
            return {"type": "ir.actions.act_window_close"}
        return move.with_context(allow_invoice_exception=True).action_post()

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}
