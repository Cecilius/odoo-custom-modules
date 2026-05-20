from odoo import _, api, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("partner_id", "invoice_line_ids", "currency_id", "company_id", "move_type")
    def _onchange_assign_journal_from_l10n_es(self):
        for move in self:
            if move.move_type != "out_invoice":
                continue

            # Reuse the Spanish localization decision instead of recalculating the threshold here.
            # Source: l10n_es_is_simplified on account.move and l10n_es_simplified_invoice_limit on res.company.
            if move.l10n_es_is_simplified and move.company_id.simplified_sales_journal_id:
                move.journal_id = move.company_id.simplified_sales_journal_id
            elif not move.l10n_es_is_simplified and move.company_id.full_sales_journal_id:
                move.journal_id = move.company_id.full_sales_journal_id

    def _journal_mismatch_message(self, simplified):
        if simplified:
            return _(
                "This invoice is classified as simplified by the Spanish localization, but it is not using the configured simplified sales journal."
            )
        return _(
            "This invoice is classified as full by the Spanish localization, but it is not using the configured full sales journal."
        )

    def _check_journal_matches_invoice_type(self):
        for move in self.filtered(lambda m: m.move_type == "out_invoice"):
            if move.l10n_es_is_simplified and move.company_id.simplified_sales_journal_id and move.journal_id != move.company_id.simplified_sales_journal_id:
                # Intentional soft block: stop posting so the user can choose whether to correct the journal or continue.
                raise UserError(move._journal_mismatch_message(True))
            if not move.l10n_es_is_simplified and move.company_id.full_sales_journal_id and move.journal_id != move.company_id.full_sales_journal_id:
                # Intentional soft block: stop posting so the user can choose whether to correct the journal or continue.
                raise UserError(move._journal_mismatch_message(False))

    def _check_customer_vat_for_full_invoice(self):
        for move in self.filtered(lambda m: m.move_type == "out_invoice"):
            limit = move.company_id.l10n_es_simplified_invoice_limit or 0.0
            if not move.l10n_es_is_simplified and move.country_code == "ES" and not move.commercial_partner_id.vat:
                # The localization already decided this is not simplified; without VAT the move should not be posted.
                raise UserError(_(
                    "This invoice exceeds the Spanish simplified invoice limit, so the customer VAT/NIF is required before posting."
                ))

    def action_post(self):
        self._check_journal_matches_invoice_type()
        self._check_customer_vat_for_full_invoice()
        return super().action_post()
