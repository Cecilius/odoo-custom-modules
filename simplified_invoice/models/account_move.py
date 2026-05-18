from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    x_invoice_mode = fields.Selection([
        ('simplified', 'Simplified'),
        ('full', 'Full'),
    ], string='Invoice Mode', default='full', copy=False)

    def _is_b2b_partner(self, partner):
        partner = partner.commercial_partner_id
        return bool(partner.vat) or partner.company_type == 'company' or partner.invoice_identification_type == 'full'

    def _must_be_full_invoice(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        is_spain = partner.country_id.code == 'ES'
        if is_spain and not self._is_b2b_partner(partner) and self.amount_total <= 400.0:
            return False
        return True

    def _tax_id_required(self):
        self.ensure_one()
        if self.move_type != 'out_invoice':
            return False
        partner = self.partner_id.commercial_partner_id
        is_spain = partner.country_id.code == 'ES'
        is_b2b = self._is_b2b_partner(partner)
        if is_spain and self.amount_total > 400.0:
            return True
        if is_b2b:
            return True
        return False

    @api.onchange('partner_id', 'invoice_line_ids', 'currency_id', 'company_id', 'move_type')
    def _onchange_assign_invoice_mode_and_journal(self):
        for move in self:
            if move.move_type != 'out_invoice':
                continue
            requires_full = move._must_be_full_invoice()
            move.x_invoice_mode = 'full' if requires_full else 'simplified'
            if not requires_full and move.company_id.simplified_sales_journal_id:
                move.journal_id = move.company_id.simplified_sales_journal_id

    def action_post(self):
        for move in self.filtered(lambda m: m.move_type == 'out_invoice'):
            related_order = self.env['sale.order'].search([('name', '=', move.invoice_origin)], limit=1)
            if related_order and related_order.invoice_review_state != 'approved':
                raise ValidationError(_('Invoice review must be approved before posting the invoice.'))
            if move.x_invoice_mode == 'full' and move._tax_id_required() and not move.partner_id.commercial_partner_id.vat:
                raise ValidationError(_('Customer tax ID (NIF/NIE/VAT) is required before posting this full invoice.'))
        return super().action_post()
