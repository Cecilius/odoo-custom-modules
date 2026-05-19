from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange("partner_id", "invoice_line_ids", "currency_id", "company_id", "move_type")
    def _onchange_assign_journal_from_l10n_es(self):
        for move in self:
            if move.move_type != "out_invoice":
                continue

            # We reuse Odoo Spain localization for the simplified/full decision.
            # See: l10n_es_is_simplified on account.move and l10n_es_simplified_invoice_limit on res.company.
            if move.l10n_es_is_simplified and move.company_id.simplified_sales_journal_id:
                move.journal_id = move.company_id.simplified_sales_journal_id
            elif not move.l10n_es_is_simplified and move.company_id.full_sales_journal_id:
                move.journal_id = move.company_id.full_sales_journal_id

    def _check_journal_matches_invoice_type(self):
        for move in self.filtered(lambda m: m.move_type == "out_invoice"):
            if move.l10n_es_is_simplified and move.company_id.simplified_sales_journal_id and move.journal_id != move.company_id.simplified_sales_journal_id:
                # Bug-fix breadcrumb: warn, don't block, because accountants may intentionally override the journal.
                move.message_post(body=_(
                    "Warning: this invoice is classified as simplified by the Spanish localization, but it is not using the configured simplified sales journal."
                ))
            if not move.l10n_es_is_simplified and move.company_id.full_sales_journal_id and move.journal_id != move.company_id.full_sales_journal_id:
                # Bug-fix breadcrumb: warn, don't block, for the same reason as the simplified case.
                move.message_post(body=_(
                    "Warning: this invoice is classified as full by the Spanish localization, but it is not using the configured full sales journal."
                ))

    def action_post(self):
        self._check_journal_matches_invoice_type()
        return super().action_post()
