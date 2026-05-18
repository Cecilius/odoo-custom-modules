from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoice_mode = fields.Selection([
        ('auto', 'Automatic'),
        ('simplified', 'Simplified'),
        ('full', 'Full'),
    ], default='auto', string='Invoice Mode')
    requires_full_invoice = fields.Boolean(compute='_compute_requires_full_invoice', store=True)
    invoice_review_state = fields.Selection([
        ('pending', 'Pending review'),
        ('approved', 'Approved'),
    ], default='pending', string='Invoice Review State', copy=False)
    tax_id_missing_warning = fields.Boolean(compute='_compute_tax_id_missing_warning', store=False)

    @api.depends('amount_total', 'partner_id.vat', 'partner_id.country_id', 'partner_id.company_type', 'invoice_mode')
    def _compute_requires_full_invoice(self):
        for order in self:
            partner = order.partner_id.commercial_partner_id
            is_spain = partner.country_id.code == 'ES'
            is_b2b = bool(partner.vat) or partner.company_type == 'company' or partner.invoice_identification_type == 'full'
            requires = True
            if is_spain and not is_b2b and order.amount_total <= 400.0:
                requires = False
            if order.invoice_mode == 'full':
                requires = True
            elif order.invoice_mode == 'simplified':
                requires = False
            order.requires_full_invoice = requires

    @api.depends('requires_full_invoice', 'partner_id.vat', 'partner_id.country_id', 'partner_id.company_type')
    def _compute_tax_id_missing_warning(self):
        for order in self:
            order.tax_id_missing_warning = order._tax_id_required() and not order.partner_id.commercial_partner_id.vat

    def _tax_id_required(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        is_spain = partner.country_id.code == 'ES'
        is_b2b = bool(partner.vat) or partner.company_type == 'company' or partner.invoice_identification_type == 'full'
        if is_spain and self.amount_total > 400.0:
            return True
        if is_b2b:
            return True
        return False

    def action_mark_invoice_review_approved(self):
        for order in self:
            if order._tax_id_required() and not order.partner_id.commercial_partner_id.vat:
                raise ValidationError(_('Tax ID is still missing. You cannot approve invoice review yet.'))
            order.invoice_review_state = 'approved'

    def action_mark_invoice_review_pending(self):
        self.write({'invoice_review_state': 'pending'})

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        self.ensure_one()
        simplified_journal = self.company_id.simplified_sales_journal_id
        if not self.requires_full_invoice and simplified_journal:
            vals['journal_id'] = simplified_journal.id
            vals['x_invoice_mode'] = 'simplified'
        else:
            vals['x_invoice_mode'] = 'full'
        return vals

    def action_confirm(self):
        result = super().action_confirm()
        self.write({'invoice_review_state': 'pending'})
        return result
