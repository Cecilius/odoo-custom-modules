# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AcquisitionBatch(models.Model):
    _name = 'resale.acquisition.batch'
    _inherit = ['mail.thread']
    _description = 'Acquisition Batch'
    _order = 'name desc'

    name = fields.Char(string='Reference', required=True, copy=False, default='New')
    partner_id = fields.Many2one('res.partner', string='Supplier', required=True)
    source_ref = fields.Char(string='Auction / Source Reference')
    acquisition_date = fields.Date(string='Acquisition Date', default=fields.Date.context_today)
    expected_arrival = fields.Date(string='Expected Arrival')
    received_date = fields.Date(string='Received Date')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    tax_regime = fields.Selection([
        ('vat', 'Regular VAT'),
        ('rebu', 'REBU'),
        ('other', 'Other / Manual review'),
    ], string='Tax Regime', default='vat', required=True)

    expected_items = fields.Integer(string='Expected Items', default=0)
    received_items = fields.Integer(
        string='Received Items',
        compute='_compute_item_counts', store=True,
    )
    item_variance = fields.Integer(
        string='Item Variance',
        compute='_compute_item_counts', store=True,
    )
    item_ids = fields.One2many('product.product', 'batch_id', string='Items')

    state = fields.Selection([
        ('ordered', 'Ordered'),
        ('awaiting', 'Awaiting Receipt'),
        ('received', 'Received / Sorting'),
        ('allocating', 'Allocating'),
        ('locked', 'Costs Locked'),
        ('done', 'Done'),
    ], string='Status', default='ordered', tracking=True)

    # Costing fields
    component_ids = fields.One2many(
        'resale.cost.component',
        'batch_id',
        string='Cost Components',
    )
    bill_ids = fields.Many2many(
        'account.move',
        'resale_acquisition_batch_account_move_rel',
        'batch_id',
        'move_id',
        string='Vendor Bills / Credits',
        domain=[('move_type', 'in', ('in_invoice', 'in_refund')), ('state', '=', 'posted')],
        copy=False,
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

    @api.depends('item_ids', 'item_ids.batch_id')
    def _compute_item_counts(self):
        for batch in self:
            batch.received_items = len(batch.item_ids)
            batch.item_variance = batch.received_items - batch.expected_items

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'resale.acquisition.batch') or 'New'
        batches = super().create(vals_list)
        for batch in batches:
            if batch.bill_ids:
                batch._sync_bill_components()
        return batches

    def write(self, vals):
        if self.filtered(lambda batch: batch.state == 'locked'):
            if {'tax_regime', 'currency_id'}.intersection(vals):
                raise AccessError(_(
                    'Locked batches cannot change tax regime or currency.'
                ))
        res = super().write(vals)
        if 'bill_ids' in vals:
            for batch in self:
                batch._sync_bill_components()
        return res

    def action_receive(self):
        for batch in self:
            if batch.state not in ('ordered', 'awaiting'):
                raise UserError(_(
                    'Batch %s must be ordered or awaiting receipt before receiving.'
                ) % batch.name)
            batch.write({
                'state': 'received',
                'received_date': fields.Date.context_today(batch),
            })

    def action_calculate_allocation(self):
        self.ensure_one()
        if self.state not in ('received', 'allocating'):
            raise UserError(_('Batch must be received before allocating costs.'))
        for item in self.item_ids:
            if not item.initial_value:
                raise UserError(_('Item %s is missing an initial value.') % item.rfb)
        mismatched = self.component_ids.filtered(
            lambda c: c.currency_id and c.currency_id != self.currency_id
        )
        if mismatched:
            raise UserError(_(
                'Cost component currencies must match the batch currency.'
            ))
        self.item_ids._allocate_cost()
        self.state = 'allocating'

    def _check_initial_evaluations_completed(self):
        self.ensure_one()
        for item in self.item_ids:
            if not item.eval_done:
                raise UserError(_(
                    'Item %s has no completed initial evaluation. '
                    'Complete initial evaluations before locking costs.'
                ) % item.rfb)

    def action_lock_costs(self):
        self.ensure_one()
        if self.state != 'allocating':
            raise UserError(_('Costs can only be locked after allocation.'))
        if not self.env.user.has_group('resale.group_resale_manager'):
            raise AccessError(_('Only Resale Managers can lock acquisition costs.'))
        self._check_initial_evaluations_completed()
        self.item_ids._lock_cost()
        self.state = 'locked'

    def action_done(self):
        self.ensure_one()
        if self.state != 'locked':
            raise UserError(_('Batch must be locked before it can be closed.'))
        self.state = 'done'

    def _sync_bill_components(self):
        self.ensure_one()
        if self.state in ('locked', 'done'):
            return
        desired_lines = self.env['account.move.line']
        for bill in self.bill_ids:
            if bill.state != 'posted':
                continue
            desired_lines |= bill.invoice_line_ids.filtered(
                lambda line: line.display_type == 'product'
            )
        existing_map = {
            component.bill_line_id.id: component
            for component in self.component_ids
            if component.bill_line_id
        }
        for component in list(self.component_ids):
            if component.bill_line_id and component.bill_line_id.id not in desired_lines.ids:
                component.unlink()
        Component = self.env['resale.cost.component']
        for line in desired_lines:
            if line.id in existing_map:
                continue
            sign = -1 if line.move_id.move_type == 'in_refund' else 1
            name = line.name or line.product_id.display_name or line.move_id.name
            Component.create({
                'batch_id': self.id,
                'bill_line_id': line.id,
                'name': name,
                'date': line.move_id.invoice_date or fields.Date.context_today(self),
                'amount_net': sign * line.price_subtotal,
                'vat_amount': sign * (line.price_total - line.price_subtotal),
                'currency_id': line.currency_id.id,
                'component_type': 'purchase',
                'include_in_allocable': True,
                'tax_treatment': 'recoverable',
            })

    def action_sync_bills(self):
        for batch in self:
            if batch.state in ('locked', 'done'):
                raise UserError(_(
                    'Cannot sync bills after costs are locked or the batch is closed.'
                ))
            batch._sync_bill_components()
        return True
