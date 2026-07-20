from odoo import _, api, models

from odoo.exceptions import UserError

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
#        currency = self.currency_id or self.company_id.currency_id
#        over_limit = currency.compare_amounts(abs(self.amount_total_signed), self.company_id.l10n_es_simplified_invoice_limit) > 0
#        if over_limit and self.country_code == "ES" and not self.commercial_partner_id.vat:
#            return True, _("This invoice exceeds the Spanish simplified invoice limit, so the customer VAT/NIF is required before posting.")
        if self.l10n_es_is_simplified and self.company_id.simplified_sales_journal_id and self.journal_id != self.company_id.simplified_sales_journal_id:
            return True, self._journal_mismatch_message(True)
        if not self.l10n_es_is_simplified and self.company_id.full_sales_journal_id and self.journal_id != self.company_id.full_sales_journal_id:
            return True, self._journal_mismatch_message(False)
        return False, ""

    def action_post(self):
        if self.env.context.get("allow_invoice_exception"):
            return super().action_post()
        self.ensure_one()
        
        if self.move_type != "out_invoice":
            return super().action_post()

        partner = self.commercial_partner_id
        is_spanish_company = self.country_code == "ES"
        is_spanish_customer = partner.country_id.code == "ES"
        is_company = bool(getattr(partner, "is_company", False))

        currency = self.currency_id or self.company_id.currency_id
        over_limit = currency.compare_amounts(abs(self.amount_total_signed), self.company_id.l10n_es_simplified_invoice_limit) > 0

        # 1) No simplified invoices for non-Spanish customers (when the company is Spanish).
        if is_spanish_company and not is_spanish_customer and self.l10n_es_is_simplified:
            raise UserError(_("You cannot create simplified invoices for customers outside Spain."))

        # 2) No simplified invoices for company-type customers (B2B).
        if is_spanish_company and is_company and self.l10n_es_is_simplified:
            raise UserError(_("You cannot create simplified invoices for company-type (B2B) customers."))

        # 3) Over-limit simplified invoices are forbidden.
        if over_limit and is_spanish_company and self.l10n_es_is_simplified:
            raise UserError(_("This invoice exceeds the Spanish simplified invoice limit, but it is marked as simplified."))

        # 4) Over-limit Spanish customers must have VAT/NIF.
        if over_limit and is_spanish_company and is_spanish_customer and not partner.vat:
            raise UserError(_("This invoice exceeds the Spanish simplified invoice limit and the customer is in Spain, so VAT/NIF is required before posting."))

        # 5) Any full invoice for Spanish customers must have VAT/NIF.
        if not self.l10n_es_is_simplified and is_spanish_company and is_spanish_customer and not partner.vat:
            raise UserError(_("Full invoices for Spanish customers require a VAT/NIF before posting."))

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
