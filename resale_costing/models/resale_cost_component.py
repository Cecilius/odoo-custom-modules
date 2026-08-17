# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, fields, models
from odoo.exceptions import AccessError


class CostComponent(models.Model):
    _name = 'resale.cost.component'
    _description = 'Batch Cost Component'
    _order = 'date, id'

    batch_id = fields.Many2one('resale.acquisition.batch', string='Batch',
                               required=True, ondelete='cascade')
    name = fields.Char(string='Description', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today)
    amount_net = fields.Monetary(string='Net Amount', required=True,
                                 currency_field='currency_id')
    vat_amount = fields.Monetary(string='VAT Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
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

    def write(self, vals):
        locked_batches = self.mapped('batch_id').filtered(
            lambda batch: batch.state == 'locked'
        )
        protected = {
            'amount_net', 'vat_amount', 'include_in_allocable',
            'tax_treatment', 'batch_id',
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
