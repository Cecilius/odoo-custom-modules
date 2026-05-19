from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('partner_id', 'invoice_line_ids', 'currency_id', 'company_id', 'move_type')
    def _onchange_assign_simplified_journal_from_l10n_es(self):
        for move in self:
            if move.move_type != 'out_invoice':
                continue
            if move.l10n_es_is_simplified and move.company_id.simplified_sales_journal_id:
                move.journal_id = move.company_id.simplified_sales_journal_id

    def action_post(self):
        for move in self.filtered(lambda m: m.move_type == 'out_invoice'):
            related_order = self.env['sale.order'].search([('name', '=', move.invoice_origin)], limit=1)
            if related_order and related_order.invoice_review_state != 'approved':
                raise ValidationError(_('Invoice review must be approved before posting the invoice.'))
            if not move.l10n_es_is_simplified and move.country_code == 'ES' and not move.commercial_partner_id.vat:
                raise ValidationError(_('Customer tax ID (NIF/NIE/VAT) is required before posting this full invoice.'))
            if move.l10n_es_is_simplified and move.company_id.simplified_sales_journal_id:
                move.journal_id = move.company_id.simplified_sales_journal_id
        return super().action_post()
