# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # --- Resale identity ---------------------------------------------------
    rfb = fields.Char(string='RFB', copy=False, index=True)
    resale_category_id = fields.Many2one(
        'product.category', string='Resale Category', index=True,
        help='Category used for RFB generation and resale reporting.',
    )
    resale_brand_id = fields.Many2one('resale.brand', string='Resale Brand')
    batch_id = fields.Many2one(
        'resale.acquisition.batch', string='Acquisition Batch',
        ondelete='restrict', index=True,
    )

    model_es = fields.Char(string='Model (Spanish)')
    model_en = fields.Char(string='Model (English)')
    asin = fields.Char(string='ASIN')
    upc = fields.Char(string='UPC')
    manufacturer_serial = fields.Char(string='Manufacturer Serial Number')
    amazon_es_url = fields.Char(string='Amazon ES Link')
    amazon_uk_url = fields.Char(string='Amazon UK Link')
    camel_url = fields.Char(string='CamelCamelCamel Link')

    # --- Lifecycle ----------------------------------------------------------
    resale_state = fields.Selection([
        ('received', 'Received'),
        ('inspecting', 'Inspecting'),
        ('needs_repair', 'Needs Repair'),
        ('needs_dismantling', 'Needs Dismantling'),
        ('ready', 'Ready for Sale'),
        ('published', 'Published'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('dismantled', 'Dismantled'),
        ('scrapped', 'Scrapped'),
        ('hold', 'Hold'),
    ], string='Resale State', default='received', tracking=True, index=True)
    photos_done = fields.Boolean(string='Photos Done', default=False)

    # --- Inline initial evaluation ------------------------------------------
    eval_done = fields.Boolean(string='Initial Evaluation Done', default=False)
    eval_date = fields.Datetime(string='Evaluation Date')
    eval_user_id = fields.Many2one('res.users', string='Evaluator')
    eval_basic_result = fields.Selection([
        ('pass', 'Basic test passed'),
        ('fault', 'Basic fault found'),
        ('unable', 'Unable to test'),
    ], string='Basic Test Result')
    eval_disposition = fields.Selection([
        ('sale', 'Potentially ready for sale'),
        ('test', 'Needs detailed testing'),
        ('repair', 'Needs repair'),
        ('dismantling', 'Needs dismantling'),
        ('scrap', 'Scrap review'),
        ('hold', 'Hold'),
    ], string='Initial Disposition')
    eval_comment = fields.Text(string='Evaluation Comment')

    # --- Final condition / assessment ---------------------------------------
    condition_id = fields.Many2one('resale.condition', string='Condition')
    functional_status = fields.Selection([
        ('working', 'Working'),
        ('repairable', 'Not working but easy to repair'),
        ('unknown', 'Unknown'),
        ('uncertain', 'Repair uncertain'),
        ('not_working', 'Not working'),
        ('parts_only', 'Tested for parts only'),
    ], string='Functional Status')
    completeness = fields.Selection([
        ('complete', 'Complete'),
        ('missing', 'Missing accessories'),
        ('unknown', 'Unknown'),
    ], string='Completeness', default='unknown')

    # --- Value / cost -------------------------------------------------------
    initial_value = fields.Monetary(string='Initial Reference Value',
                                    currency_field='currency_id')
    condition_factor = fields.Float(string='Condition Factor', default=1.0)
    functional_factor = fields.Float(string='Functional Factor', default=1.0)
    completeness_factor = fields.Float(string='Completeness Factor', default=1.0)
    adjusted_value = fields.Monetary(
        string='Adjusted Value',
        compute='_compute_adjusted_value', store=True,
        currency_field='currency_id',
    )

    acquisition_cost = fields.Monetary(string='Acquisition Cost',
                                       currency_field='currency_id')
    cost_status = fields.Selection([
        ('pending', 'Pending'),
        ('provisional', 'Provisional'),
        ('locked', 'Locked'),
        ('legacy_locked', 'Legacy Locked'),
        ('legacy_estimated', 'Legacy Estimated'),
    ], string='Cost Status', default='pending')

    repair_cost = fields.Monetary(string='Repair Cost', currency_field='currency_id')
    parts_cost = fields.Monetary(string='Parts Cost', currency_field='currency_id')

    min_price = fields.Monetary(string='Minimum Price', currency_field='currency_id')
    recommended_price = fields.Monetary(string='Recommended Price',
                                        currency_field='currency_id')

    warranty_policy_id = fields.Many2one('resale.warranty.policy', string='Warranty Policy')
    warranty_start = fields.Date(string='Warranty Start')
    warranty_end = fields.Date(string='Warranty End')

    source_product_id = fields.Many2one(
        'product.product', string='Source Item',
        help='Original item when this product is a recovered part.',
    )
    component_ids = fields.One2many(
        'product.product', 'source_product_id', string='Recovered Parts',
    )
    detailed_test_ids = fields.One2many(
        'resale.detailed.test', 'product_id', string='Detailed Tests',
    )

    migration_status = fields.Selection([
        ('not_reviewed', 'Not Reviewed'),
        ('migrated_unsold', 'Migrated - Unsold'),
        ('migrated_sold', 'Migrated - Sold'),
        ('migrated_warranty', 'Migrated - Warranty Active'),
        ('duplicate', 'Duplicate'),
        ('obsolete', 'Obsolete'),
    ], string='Migration Status', default='not_reviewed')
    legacy_reference = fields.Char(string='Legacy Reference')

    # --- Constraints / compute ----------------------------------------------
    @api.constrains('rfb')
    def _check_rfb_unique(self):
        for product in self:
            if not product.rfb:
                continue
            if self.search_count([('rfb', '=', product.rfb), ('id', '!=', product.id)]):
                raise ValidationError(_('RFB %s is already assigned.') % product.rfb)

    @api.depends('initial_value', 'condition_factor', 'functional_factor', 'completeness_factor')
    def _compute_adjusted_value(self):
        for product in self:
            product.adjusted_value = (
                product.initial_value
                * product.condition_factor
                * product.functional_factor
                * product.completeness_factor
            )

    @api.onchange('condition_id')
    def _onchange_condition_id(self):
        if self.condition_id:
            self.condition_factor = self.condition_id.condition_factor
            if self.condition_id.warranty_policy_id and not self.warranty_policy_id:
                self.warranty_policy_id = self.condition_id.warranty_policy_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('resale_category_id') and not vals.get('rfb'):
                category = self.env['product.category'].browse(vals['resale_category_id'])
                sequence = category._get_or_create_rfb_sequence()
                rfb = sequence.next_by_id()
                vals['rfb'] = rfb
            if vals.get('rfb'):
                vals['default_code'] = vals['rfb']
                vals['barcode'] = vals['rfb']
                vals.setdefault('type', 'consu')
                vals.setdefault('is_storable', True)
        return super().create(vals_list)

    def write(self, vals):
        locked = self.filtered(
            lambda p: p.cost_status in ('locked', 'legacy_locked')
        )
        if locked and {'acquisition_cost', 'cost_status'}.intersection(vals):
            if not self.env.context.get('resale_lock_cost'):
                raise AccessError(_(
                    'Locked acquisition costs cannot be edited directly. '
                    'Create a cost adjustment instead.'
                ))
        if vals.get('cost_status') in ('locked', 'legacy_locked'):
            if not self.env.context.get('resale_lock_cost'):
                raise AccessError(_('Use the cost-lock action to lock item costs.'))
        if 'rfb' in vals and vals['rfb']:
            vals['default_code'] = vals['rfb']
            vals['barcode'] = vals['rfb']
        return super().write(vals)

    # --- Business actions ---------------------------------------------------
    def _state_from_eval_disposition(self):
        self.ensure_one()
        return {
            'sale': 'ready',
            'test': 'inspecting',
            'repair': 'needs_repair',
            'dismantling': 'needs_dismantling',
            'scrap': 'scrapped',
            'hold': 'hold',
        }.get(self.eval_disposition, 'inspecting')

    def action_complete_evaluation(self):
        for product in self:
            if product.eval_done:
                continue
            if not product.eval_basic_result:
                raise UserError(_('Please select a basic test result.'))
            if not product.eval_disposition:
                raise UserError(_('Please select an initial disposition.'))
            vals = {
                'eval_done': True,
                'eval_date': fields.Datetime.now(),
                'eval_user_id': self.env.user.id,
                'resale_state': product._state_from_eval_disposition(),
            }
            if product.condition_id:
                vals['condition_factor'] = product.condition_id.condition_factor
                if product.condition_id.warranty_policy_id and not product.warranty_policy_id:
                    vals['warranty_policy_id'] = product.condition_id.warranty_policy_id.id
            product.write(vals)
        return True

    def action_start_detailed_test(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'resale.detailed.test',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_product_id': self.id},
        }

    def _allocate_cost(self):
        for batch in self.mapped('batch_id'):
            items = batch.item_ids
            total_adjusted = sum(items.mapped('adjusted_value')) or 0.0
            if total_adjusted:
                for item in items:
                    item.acquisition_cost = (
                        batch.allocable_cost * item.adjusted_value / total_adjusted
                    )
                    item.cost_status = 'provisional'

    def _lock_cost(self):
        if not self.env.user.has_group('resale.group_resale_manager'):
            raise AccessError(_('Only Resale Managers can lock acquisition costs.'))
        for product in self:
            if product.cost_status in ('locked', 'legacy_locked'):
                continue
            product.with_context(resale_lock_cost=True).write({
                'cost_status': 'locked',
            })
