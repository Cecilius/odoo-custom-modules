# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AcquisitionBatch(models.Model):
    _inherit = 'resale.acquisition.batch'

    component_ids = fields.One2many(
        'resale.cost.component',
        'batch_id',
        string='Cost Components',
    )
    allocable_cost = fields.Monetary(
        string='Allocable Cost',
        compute='_compute_cost_totals',
        store=True,
        currency_field='currency_id',
    )
    total_cash = fields.Monetary(
        string='Total Cash',
        compute='_compute_cost_totals',
        store=True,
        currency_field='currency_id',
    )

    @api.depends(
        'component_ids.amount_net',
        'component_ids.vat_amount',
        'component_ids.include_in_allocable',
    )
    def _compute_cost_totals(self):
        for batch in self:
            allocable = total_cash = 0.0
            for component in batch.component_ids:
                total_cash += component.amount_net + component.vat_amount
                if component.include_in_allocable:
                    allocable += component.amount_net
            batch.allocable_cost = allocable
            batch.total_cash = total_cash

    def action_calculate_allocation(self):
        self.ensure_one()
        if self.received_items < self.expected_items and self.expected_items:
            raise UserError(_('Not all expected items have been received.'))
        for item in self.item_ids:
            if not item.initial_value:
                raise UserError(_('Item %s is missing an initial value.') % item.rfb)
        self.item_ids._allocate_cost()

    def action_lock_costs(self):
        self.ensure_one()
        if not self.env.user.has_group('resale_core.group_resale_manager'):
            raise AccessError(_('Only Resale Managers can lock acquisition costs.'))
        self.item_ids._lock_cost()
        self.state = 'locked'

    def write(self, vals):
        if self.filtered(lambda batch: batch.state == 'locked'):
            if {'tax_regime', 'currency_id'}.intersection(vals):
                raise AccessError(_(
                    'Locked batches cannot change tax regime or currency.'
                ))
        return super().write(vals)
