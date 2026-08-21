# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models, Command
from odoo.exceptions import AccessError, UserError, ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # --- Resale identity ---------------------------------------------------
    rfb = fields.Char(string='RFB', copy=False, index=True)
    resale_brand_id = fields.Many2one('resale.brand', string='Resale Brand')
    brand_value_id = fields.Many2one(
        'product.attribute.value',
        string='Brand',
        compute='_compute_brand_value',
        inverse='_inverse_brand_value',
    )
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
    condition_grade_value_id = fields.Many2one(
        'product.attribute.value',
        string='Condition Grade',
        compute='_compute_condition_grade_value',
        inverse='_inverse_condition_grade_value',
    )
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

    def _condition_grade_attribute(self):
        return self.env.ref(
            'resale.product_attribute_condition_grade',
            raise_if_not_found=False,
        )

    def _brand_attribute(self):
        return self.env.ref('resale.product_attribute_brand', raise_if_not_found=False)

    @api.depends('product_tmpl_id.attribute_line_ids.value_ids')
    def _compute_brand_value(self):
        attribute = self._brand_attribute()
        for product in self:
            line = product.product_tmpl_id.attribute_line_ids.filtered(
                lambda item: attribute and item.attribute_id == attribute
            )[:1]
            product.brand_value_id = line.value_ids[:1] if line else False

    def _set_brand_value(self, value):
        self.ensure_one()
        attribute = self._brand_attribute()
        if not attribute or not value or value.attribute_id != attribute:
            return
        line = self.product_tmpl_id.attribute_line_ids.filtered(
            lambda item: item.attribute_id == attribute
        )[:1]
        if line:
            line.value_ids = [Command.set([value.id])]
        else:
            self.env['product.template.attribute.line'].create({
                'product_tmpl_id': self.product_tmpl_id.id,
                'attribute_id': attribute.id,
                'value_ids': [Command.link(value.id)],
            })
        legacy_brand = self.env['resale.brand'].search([
            ('name', '=ilike', value.name),
        ], limit=1)
        if legacy_brand:
            self.with_context(skip_brand_sync=True).write({
                'resale_brand_id': legacy_brand.id,
            })

    def _sync_brand_attribute_from_legacy(self):
        BrandValue = self.env['product.attribute.value']
        attribute = self._brand_attribute()
        if not attribute:
            return
        for product in self.filtered('resale_brand_id'):
            value = BrandValue.search([
                ('attribute_id', '=', attribute.id),
                ('name', '=ilike', product.resale_brand_id.name),
            ], limit=1)
            if not value:
                value = BrandValue.create({
                    'name': product.resale_brand_id.name,
                    'attribute_id': attribute.id,
                    'resale_is_brand': True,
                })
            product._set_brand_value(value)

    @api.model
    def _migrate_brand_attribute_all(self):
        self.search([('resale_brand_id', '!=', False)])._sync_brand_attribute_from_legacy()

    @api.depends('product_tmpl_id.attribute_line_ids.value_ids')
    def _compute_condition_grade_value(self):
        attribute = self._condition_grade_attribute()
        for product in self:
            line = product.product_tmpl_id.attribute_line_ids.filtered(
                lambda item: attribute and item.attribute_id == attribute
            )[:1]
            product.condition_grade_value_id = line.value_ids[:1] if line else False

    def _apply_condition_grade_metadata(self, value, include_policy=True):
        self.ensure_one()
        vals = {}
        if value.resale_condition_id:
            vals['condition_id'] = value.resale_condition_id.id
        if include_policy and value.resale_warranty_policy_id:
            vals['warranty_policy_id'] = value.resale_warranty_policy_id.id
        if value.resale_condition_factor:
            vals['condition_factor'] = value.resale_condition_factor
        if vals:
            self.write(vals)

    def _set_condition_grade_value(self, value):
        self.ensure_one()
        attribute = self._condition_grade_attribute()
        if not attribute or not value or value.attribute_id != attribute:
            return
        line = self.product_tmpl_id.attribute_line_ids.filtered(
            lambda item: item.attribute_id == attribute
        )[:1]
        if line:
            line.value_ids = [Command.set([value.id])]
        else:
            self.env['product.template.attribute.line'].create({
                'product_tmpl_id': self.product_tmpl_id.id,
                'attribute_id': attribute.id,
                'value_ids': [Command.link(value.id)],
            })
        self._apply_condition_grade_metadata(
            value,
            include_policy=self.type != 'service',
        )

    def _sync_condition_grade_from_condition(self):
        for product in self:
            if not product.condition_id:
                continue
            attribute = self._condition_grade_attribute()
            if not attribute:
                continue
            value = self.env['product.attribute.value'].search([
                ('attribute_id', '=', attribute.id),
                ('resale_condition_id', '=', product.condition_id.id),
            ], limit=1)
            if value:
                product._set_condition_grade_value(value)

    @api.model
    def _ensure_generic_warranty_all(self):
        service_policy = self.env.ref(
            'resale.warranty_service_3_months',
            raise_if_not_found=False,
        )
        goods_policy = self.env.ref(
            'resale.warranty_36_months',
            raise_if_not_found=False,
        )
        for product in self.search([]):
            if product.condition_id:
                product._sync_condition_grade_from_condition()
            elif product.condition_grade_value_id:
                product._apply_condition_grade_metadata(
                    product.condition_grade_value_id,
                    include_policy=product.type != 'service',
                )
            if not product.warranty_policy_id:
                policy = service_policy if product.type == 'service' else goods_policy
                if policy:
                    product.warranty_policy_id = policy

    def _inverse_condition_grade_value(self):
        for product in self:
            product._set_condition_grade_value(product.condition_grade_value_id)

    def _inverse_brand_value(self):
        for product in self:
            product._set_brand_value(product.brand_value_id)

    @api.model_create_multi
    def create(self, vals_list):
        explicit_policies = [vals.get('warranty_policy_id') for vals in vals_list]
        for vals in vals_list:
            if vals.get('categ_id') and not vals.get('rfb'):
                category = self.env['product.category'].browse(vals['categ_id'])
                sequence = category._get_or_create_rfb_sequence()
                if sequence:
                    vals['rfb'] = sequence.next_by_id()
            if vals.get('rfb'):
                vals['default_code'] = vals['rfb']
                vals['barcode'] = vals['rfb']
                vals.setdefault('type', 'consu')
                vals.setdefault('is_storable', True)
        products = super().create(vals_list)
        service_policy = self.env.ref(
            'resale.warranty_service_3_months',
            raise_if_not_found=False,
        )
        # Products created without explicit categ_id may still get a resale default category.
        for product, explicit_policy in zip(products, explicit_policies):
            if product.resale_brand_id:
                product._sync_brand_attribute_from_legacy()
            if not product.rfb and product.categ_id.rfb_prefix:
                sequence = product.categ_id._get_or_create_rfb_sequence()
                if sequence:
                    rfb = sequence.next_by_id()
                    product.write({'rfb': rfb, 'default_code': rfb, 'barcode': rfb})
            if product.condition_grade_value_id:
                if explicit_policy:
                    product.warranty_policy_id = explicit_policy
                product._apply_condition_grade_metadata(
                    product.condition_grade_value_id,
                    include_policy=(
                        not explicit_policy and product.type != 'service'
                    ),
                )
            if product.type == 'service' and not explicit_policy and service_policy:
                product.warranty_policy_id = service_policy
        return products

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

    def action_open_standard_product(self):
        self.ensure_one()
        return self.get_formview_action()

    def action_open_resale_item(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(self.env.ref('resale.view_resale_product_form').id, 'form')],
            'target': 'current',
        }

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
