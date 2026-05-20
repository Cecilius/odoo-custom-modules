from odoo import _, api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("partner_id", "invoice_line_ids", "currency_id", "company_id", "move_type")
    def _onchange_assign_journal_from_l10n_es(self):
        for move in self:
            if move.move_type != "out_invoice":
                continue
            if move.l10n_es_is_simplified and move.company_id.simplified_sales_journal_id:
                move.journal_id = move.company_id.simplified_sales_journal_id
            elif not move.l10n_es_is_simplified and move.company_id.full_sales_journal_id:
                move.journal_id = move.company_id.full_sales_journal_id

    def _journal_mismatch_message(self, simplified):
        if simplified:
            return _("This invoice is classified as simplified by the Spanish localization, but it is not using the configured simplified sales journal.")
        return _("This invoice is classified as full by the Spanish localization, but it is not using the configured full sales journal.")

    def _needs_confirmation_wizard(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            return False, ""
        currency = self.currency_id or self.company_id.currency_id
        over_limit = currency.compare_amounts(abs(self.amount_total_signed), self.company_id.l10n_es_simplified_invoice_limit) > 0
        if self.l10n_es_is_simplified and self.company_id.simplified_sales_journal_id and self.journal_id != self.company_id.simplified_sales_journal_id:
            return True, self._journal_mismatch_message(True)
        if not self.l10n_es_is_simplified and self.company_id.full_sales_journal_id and self.journal_id != self.company_id.full_sales_journal_id:
            return True, self._journal_mismatch_message(False)
        if over_limit and self.country_code == "ES" and not self.commercial_partner_id.vat:
            return True, _("This invoice exceeds the Spanish simplified invoice limit, so the customer VAT/NIF is required before posting.")
        return False, ""

    def action_post(self):
        if self.env.context.get("allow_invoice_exception"):
            return super().action_post()
        self.ensure_one()
        needs_wizard, message = self._needs_confirmation_wizard()
        if needs_wizard:
            return {
                "type": "ir.actions.act_window",
                "name": _("Confirm Invoice Posting"),
                "res_model": "simplified.invoice.post.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {"default_move_id": self.id, "default_message": message},
            }
        return super().action_post()
