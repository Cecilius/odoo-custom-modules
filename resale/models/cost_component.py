# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class CostComponent(models.Model):
    _name = 'resale.cost.component'
    _description = 'Batch Cost Component'
    _order = 'date, id'

    batch_id = fields.Many2one('resale.acquisition.batch', string='Batch',
                               required=True, ondelete='cascade')
    name = fields.Char(string='Description', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today)
    amount_net = fields.Monetary(
        string='Net Amount',
        required=True,
        currency_field='currency_id',
        compute='_compute_from_bill_line',
        store=True,
        readonly=False,
    )
    vat_amount = fields.Monetary(
        string='VAT Amount',
        currency_field='currency_id',
        compute='_compute_from_bill_line',
        store=True,
        readonly=False,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        compute='_compute_from_bill_line',
        store=True,
        readonly=False,
    )
    component_type = fields.Selection([
        ('purchase', 'Purchase'),
        ('shipping', 'Shipping'),
        ('service', 'Service Fee'),
        ('other', 'Other'),
    ], string='Type', required=True)
    include_in_allocable = fields.Boolean(string='Include in Allocable Cost', default=True)
    tax_treatment = fields.Selection([
        ('recoverable', 'Recoverable VAT'),
        ('reverse_charge', 'Reverse Charge'),
        ('none', 'No VAT'),
        ('review', 'Manual Review'),
    ], string='Tax Treatment', default='recoverable')
    source_document = fields.Char(string='Source Document')

    bill_id = fields.Many2one(
        'account.move',
        string='Vendor Bill',
        related='bill_line_id.move_id',
        store=True,
        readonly=True,
    )
    move_type = fields.Selection(
        related='bill_id.move_type',
        string='Document Type',
        store=True,
        readonly=True,
    )
    bill_line_id = fields.Many2one(
        'account.move.line',
        string='Bill Line',
        domain="[('move_id.move_type','in',('in_invoice','in_refund')),('display_type','=','product')]",
        index=True,
        copy=False,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        related='bill_id.partner_id',
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        related='bill_line_id.product_id',
        store=True,
        readonly=True,
    )

    _bill_line_uniq = models.Constraint(
        'unique(bill_line_id)',
        'A bill line can only be imported once.',
    )

    @api.depends('bill_line_id', 'bill_line_id.price_subtotal',
                 'bill_line_id.price_total', 'bill_line_id.currency_id',
                 'bill_line_id.move_id.invoice_date', 'bill_line_id.name',
                 'bill_line_id.move_id.move_type', 'batch_id.state')
    def _compute_from_bill_line(self):
        for component in self:
            line = component.bill_line_id
            if not line:
                continue
            if component.batch_id.state in ('locked', 'done'):
                continue
            sign = -1 if line.move_id.move_type == 'in_refund' else 1
            component.name = line.name or component.name
            component.date = line.move_id.invoice_date or component.date
            component.amount_net = sign * line.price_subtotal
            component.vat_amount = sign * (line.price_total - line.price_subtotal)
            component.currency_id = line.currency_id

    @api.constrains('bill_line_id', 'batch_id')
    def _check_bill_line_batch(self):
        for component in self:
            if not component.bill_line_id:
                continue
            if component.bill_id.state != 'posted':
                raise UserError(_(
                    'Cost component %s is linked to a vendor bill that is not posted.'
                ) % component.name)
            if component.bill_id.move_type not in ('in_invoice', 'in_refund'):
                raise UserError(_(
                    'Cost component %s must be linked to a vendor bill or credit note.'
                ) % component.name)

    def write(self, vals):
        locked_batches = self.mapped('batch_id').filtered(
            lambda batch: batch.state == 'locked'
        )
        protected = {
            'amount_net', 'vat_amount', 'include_in_allocable',
            'tax_treatment', 'batch_id', 'bill_line_id',
        }
        if locked_batches and protected.intersection(vals):
            raise AccessError(_(
                'Cost components cannot be edited after batch locking. '
                'Create a cost adjustment instead.'
            ))
        return super().write(vals)

    def unlink(self):
        if self.mapped('batch_id').filtered(lambda batch: batch.state == 'locked'):
            raise AccessError(_('Cost components cannot be deleted after batch locking.'))
        return super().unlink()
