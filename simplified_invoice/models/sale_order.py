from odoo import _, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoice_review_state = fields.Selection([
        ('pending', 'Pending review'),
        ('approved', 'Approved'),
    ], default='pending', string='Invoice Review State', copy=False)
    tax_id_missing_warning = fields.Boolean(compute='_compute_tax_id_missing_warning', store=False)

    def _compute_tax_id_missing_warning(self):
        for order in self:
            order.tax_id_missing_warning = order._tax_id_required() and not order.partner_id.commercial_partner_id.vat

    def _tax_id_required(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        is_company = partner.company_type == 'company'
        if self.company_id.country_code == 'ES' and partner.country_id.code == 'ES' and self.amount_total > self.company_id.l10n_es_simplified_invoice_limit:
            return True
        if partner.vat or is_company:
            return True
        return False

    def action_mark_invoice_review_approved(self):
        for order in self:
            if order._tax_id_required() and not order.partner_id.commercial_partner_id.vat:
                raise ValidationError(_('Tax ID is still missing. You cannot approve invoice review yet.'))
            order.invoice_review_state = 'approved'

    def action_mark_invoice_review_pending(self):
        self.write({'invoice_review_state': 'pending'})

    def action_confirm(self):
        result = super().action_confirm()
        self.write({'invoice_review_state': 'pending'})
        return result
