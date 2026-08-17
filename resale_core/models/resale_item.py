# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ResaleItem(models.Model):
    _name = 'resale.item'
    _inherit = ['mail.thread']
    _description = 'Resale Item'
    _order = 'rfb'

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    rfb = fields.Char(string='RFB', required=True, copy=False, index=True)
    barcode = fields.Char(string='Barcode', copy=False)
    label_id = fields.Many2one('resale.rfb.label', string='RFB Label', copy=False)

    batch_id = fields.Many2one('resale.acquisition.batch', string='Acquisition Batch',
                               ondelete='restrict', index=True)
    category_id = fields.Many2one('resale.category', string='Category', required=True)
    brand_id = fields.Many2one('resale.brand', string='Brand')

    product_id = fields.Many2one('product.product', string='Odoo Product',
                                 ondelete='restrict', index=True)
    lot_id = fields.Many2one('stock.lot', string='Lot / Serial Number')
    location_id = fields.Many2one('stock.location', string='Location')

    model_es = fields.Char(string='Model (Spanish)')
    model_en = fields.Char(string='Model (English)')
    asin = fields.Char(string='ASIN')
    ean = fields.Char(string='EAN')
    upc = fields.Char(string='UPC')
    manufacturer_serial = fields.Char(string='Manufacturer Serial Number')
    amazon_es_url = fields.Char(string='Amazon ES Link')
    amazon_uk_url = fields.Char(string='Amazon UK Link')
    camel_url = fields.Char(string='CamelCamelCamel Link')

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
    approved_price = fields.Monetary(string='Approved Price', currency_field='currency_id')

    warranty_policy_id = fields.Many2one('resale.warranty.policy', string='Warranty Policy')
    warranty_start = fields.Date(string='Warranty Start')
    warranty_end = fields.Date(string='Warranty End')

    sold_delivery_id = fields.Many2one('stock.picking', string='Delivery')
    sold_date = fields.Datetime(string='Sold Date')

    source_item_id = fields.Many2one('resale.item', string='Source Item')
    component_ids = fields.One2many('resale.item', 'source_item_id', string='Recovered Parts')

    migration_status = fields.Selection([
        ('not_reviewed', 'Not Reviewed'),
        ('migrated_unsold', 'Migrated - Unsold'),
        ('migrated_sold', 'Migrated - Sold'),
        ('migrated_warranty', 'Migrated - Warranty Active'),
        ('duplicate', 'Duplicate'),
        ('obsolete', 'Obsolete'),
    ], string='Migration Status', default='not_reviewed')
    legacy_reference = fields.Char(string='Legacy Reference')

    state = fields.Selection([
        ('intake', 'Intake'),
        ('identifying', 'Identifying'),
        ('initial_eval', 'Initial Evaluation'),
        ('detailed_test', 'Detailed Testing'),
        ('needs_repair', 'Needs Repair'),
        ('needs_dismantling', 'Needs Dismantling'),
        ('photo', 'Ready for Photography'),
        ('pricing', 'Ready for Pricing'),
        ('publish', 'Ready to Publish'),
        ('published', 'Published'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('warranty', 'Under Warranty'),
        ('dismantled', 'Dismantled'),
        ('scrapped', 'Scrapped'),
        ('archived', 'Archived'),
    ], string='Lifecycle State', default='intake', tracking=True, index=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    @api.depends('category_id', 'brand_id', 'model_es', 'rfb')
    def _compute_name(self):
        for item in self:
            parts = [item.rfb]
            if item.brand_id:
                parts.append(item.brand_id.name)
            if item.model_es:
                parts.append(item.model_es)
            item.name = ' - '.join(parts)

    @api.depends('initial_value', 'condition_factor', 'functional_factor', 'completeness_factor')
    def _compute_adjusted_value(self):
        for item in self:
            item.adjusted_value = (
                item.initial_value
                * item.condition_factor
                * item.functional_factor
                * item.completeness_factor
            )

    _rfb_uniq = models.Constraint(
        'unique(rfb)',
        'RFB must be unique.',
    )
    _product_uniq = models.Constraint(
        'unique(product_id)',
        'Each product can have only one resale item.',
    )
    _label_uniq = models.Constraint(
        'unique(label_id)',
        'Each RFB label can be assigned to only one item.',
    )

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
        if not self.env.user.has_group('resale_core.group_resale_manager'):
            raise AccessError(_('Only Resale Managers can lock acquisition costs.'))
        for item in self:
            if item.cost_status in ('locked', 'legacy_locked'):
                continue
            item.with_context(resale_lock_cost=True).write({
                'cost_status': 'locked',
            })

    def write(self, vals):
        locked = self.filtered(
            lambda item: item.cost_status in ('locked', 'legacy_locked')
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
        return super().write(vals)
