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
            return _(
                "This invoice is classified as simplified by the Spanish localization, "
                "but it is not using the configured simplified sales journal."
            )
        return _(
            "This invoice is classified as full by the Spanish localization, "
            "but it is not using the configured full sales journal."
        )

    @api.depends("partner_id", "line_ids.balance", "reversed_entry_id")
    def _compute_l10n_es_is_simplified(self):
        """Keep Odoo's rule, but limit its generic EU branch to Spain."""
        res = super()._compute_l10n_es_is_simplified()

        simplified_partner = self.env.ref(
            "l10n_es.partner_simplified", raise_if_not_found=False
        )
        european_countries = self.env.ref("base.europe").country_ids

        for move in self:
            generic_eu_rule = (
                move.l10n_es_is_simplified
                and move.country_code == "ES"
                and move.move_type in ("out_invoice", "out_refund")
                and not move.commercial_partner_id.vat
                and move.commercial_partner_id.country_id in european_countries
                and move.commercial_partner_id.country_id.code != "ES"
                and move.partner_id != simplified_partner
                and not move.reversed_entry_id.l10n_es_is_simplified
            )
            if generic_eu_rule:
                move.l10n_es_is_simplified = False
        return res

    def _is_over_simplified_limit(self):
        """Return whether the invoice total exceeds the Spanish simplified limit.

        The limit itself is allowed (an invoice of exactly the limit may still be
        simplified); only amounts strictly above it require a full invoice.
        """
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        limit = self.company_id.l10n_es_simplified_invoice_limit
        return currency.compare_amounts(abs(self.amount_total_signed), limit) > 0

    def _check_simplified_invoice_rules(self):
        """Enforce the Spanish simplified/full invoice rules on customer invoices.

        Runs from ``_post`` so that every posting path (form button, list-view
        batch posting, auto-post cron, online payment) applies the same rules.
        """
        for move in self.filtered(lambda m: m.move_type == "out_invoice" and m.country_code == "ES"):
            partner = move.commercial_partner_id
            is_spanish_customer = partner.country_id.code == "ES"
            over_limit = move._is_over_simplified_limit()

            if move.l10n_es_is_simplified:
                if not is_spanish_customer:
                    raise UserError(_(
                        "%(invoice)s: you cannot create simplified invoices for customers outside Spain.",
                        invoice=move.display_name,
                    ))
                if partner.is_company:
                    raise UserError(_(
                        "%(invoice)s: you cannot create simplified invoices for company-type (B2B) customers.",
                        invoice=move.display_name,
                    ))
                if over_limit:
                    raise UserError(_(
                        "%(invoice)s exceeds the Spanish simplified invoice limit, but it is marked as simplified.",
                        invoice=move.display_name,
                    ))
            elif is_spanish_customer and not partner.vat:
                raise UserError(_(
                    "%(invoice)s: full invoices for Spanish customers require a VAT/NIF before posting.",
                    invoice=move.display_name,
                ))

    def _needs_confirmation_wizard(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            return False, ""
        company = self.company_id
        if (
            self.l10n_es_is_simplified
            and company.simplified_sales_journal_id
            and self.journal_id != company.simplified_sales_journal_id
        ):
            return True, self._journal_mismatch_message(True)
        if (
            not self.l10n_es_is_simplified
            and company.full_sales_journal_id
            and self.journal_id != company.full_sales_journal_id
        ):
            return True, self._journal_mismatch_message(False)
        return False, ""

    def _post(self, soft=True):
        if not self.env.context.get("allow_invoice_exception"):
            self._check_simplified_invoice_rules()
        return super()._post(soft=soft)

    def action_post(self):
        """Ask for confirmation when a single invoice uses the wrong sales journal.

        The confirmation wizard is only offered for one invoice posted from the
        form; batch and automated posting keep Odoo's standard behaviour.
        """
        if (
            not self.env.context.get("allow_invoice_exception")
            and len(self) == 1
            and self.move_type == "out_invoice"
        ):
            # Surface hard rule violations before offering the journal wizard.
            self._check_simplified_invoice_rules()
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
