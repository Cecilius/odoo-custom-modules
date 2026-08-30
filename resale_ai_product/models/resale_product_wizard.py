"""Wizard for identifying resale products and resolving identifier conflicts."""

from odoo import _, api, Command, fields, models
from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.addons.resale_ai_base.models.ai_service import ResaleAIRequestError
from odoo.exceptions import UserError, ValidationError


class ResearchLLMApiService(LLMApiService):
    """Give grounded research requests a configurable timeout."""

    def _request(self, *args, timeout=30, **kwargs):
        configured_timeout = self.env['ir.config_parameter'].sudo().get_param(
            'resale_ai_product.request_timeout', '90'
        )
        try:
            configured_timeout = max(int(configured_timeout), 30)
        except (TypeError, ValueError):
            configured_timeout = 90
        return super()._request(*args, timeout=max(timeout, configured_timeout), **kwargs)


class ResaleProductWizardMatch(models.TransientModel):
    _name = 'resale.product.wizard.match'
    _description = 'Resale Product Identifier Match'

    wizard_id = fields.Many2one('resale.product.wizard', required=True, ondelete='cascade')
    identifier = fields.Char(string='Identifier', readonly=True)
    product_id = fields.Many2one('resale.product', string='Existing product', readonly=True)


class ResaleProductWizardComparison(models.TransientModel):
    _name = 'resale.product.wizard.comparison'
    _description = 'Resale Product AI Comparison'

    wizard_id = fields.Many2one('resale.product.wizard', required=True, ondelete='cascade')
    field_label = fields.Char(string='Field', readonly=True)
    ai_value = fields.Char(string='AI proposal', readonly=True)
    product_a_value = fields.Char(string='Product A value', readonly=True)
    product_b_value = fields.Char(string='Product B value', readonly=True)
    product_c_value = fields.Char(string='Product C value', readonly=True)


class ResaleProductWizard(models.TransientModel):
    """Research products, compare matches, and create or update resale records."""
    _name = 'resale.product.wizard'
    _description = 'AI Resale Product Research'

    ean = fields.Char(string='EAN')
    upc = fields.Char(string='UPC')
    asin = fields.Char(string='ASIN')
    description = fields.Text(string='Product identification details')
    exclude_description = fields.Boolean(
        string='Exclude description from AI response',
        help='When enabled, the agent will not research or return a product description. The identification details above are still sent.',
    )
    additional_question = fields.Text(string='Answer to AI question')
    state = fields.Selection([('draft', 'Ready'), ('matched', 'Internal match'), ('researched', 'AI result'), ('question', 'More details required'), ('conflict', 'Identifier conflict'), ('comparison', 'AI comparison'), ('error', 'Research failed')], default='draft', required=True)
    result_name = fields.Char(string='Product name', translate=True)
    result_description = fields.Text(string='AI product description', translate=True)
    result_category_id = fields.Many2one(
        'product.category', string='Product category',
        domain="[('category_code', '!=', False)]",
    )
    brand_attribute_id = fields.Many2one(
        'product.attribute', compute='_compute_brand_attribute_id', readonly=True,
    )
    result_brand_value_id = fields.Many2one(
        'product.attribute.value', string='Product brand',
        domain="[('attribute_id', '=', brand_attribute_id)]",
    )
    result_ean = fields.Char(string='Result EAN')
    result_upc = fields.Char(string='Result UPC')
    result_asin = fields.Char(string='Result ASIN')
    result_retail_price = fields.Float(string='Reference price')
    result_launch_year = fields.Char(string='Launch year')
    translation_preview = fields.Text(string='Names in installed languages', readonly=True)
    description_translation_preview = fields.Text(
        string='Descriptions in installed languages', readonly=True,
    )
    ai_question = fields.Text(string='AI question', readonly=True)
    ai_response = fields.Text(string='AI response', readonly=True)
    research_notice = fields.Text(string='Research status', readonly=True)
    match_line_ids = fields.One2many(
        'resale.product.wizard.match', 'wizard_id', string='Identifier matches', readonly=True,
    )
    match_conflict_message = fields.Text(string='Matching conflict', readonly=True)
    comparison_ids = fields.One2many(
        'resale.product.wizard.comparison', 'wizard_id', string='AI comparison', readonly=True,
    )
    comparison_product_ids = fields.Many2many(
        'resale.product', string='Products in comparison', readonly=True,
    )
    comparison_target_product_id = fields.Many2one(
        'resale.product', string='Apply proposal to',
        domain="[('id', 'in', comparison_product_ids)]",
    )
    conflict_product_id = fields.Many2one('resale.product', readonly=True)
    conflict_field = fields.Selection(
        [('ean', 'EAN'), ('upc', 'UPC'), ('asin', 'ASIN')], readonly=True,
    )
    match_existing_product_id = fields.Many2one('resale.product', readonly=True)
    from_template = fields.Boolean(
        string='Launched from product template',
        default=lambda self: self.env.context.get('from_template', False),
        help='Set when the wizard is opened from a product.template, so a linked product.template is also created.',
    )
    conflict_type = fields.Selection(
        [('mismatch', 'Existing value differs'), ('missing', 'Value is missing')], readonly=True,
    )
    conflict_supplied_value = fields.Char(readonly=True)
    conflict_existing_value = fields.Char(readonly=True)

    @api.depends()
    def _compute_brand_attribute_id(self):
        value = self.env['ir.config_parameter'].sudo().get_param(
            'resale_attributes.brand_attribute_id'
        )
        attribute = self.env['product.attribute'].browse(int(value)).exists() if value and value.isdigit() else self.env['product.attribute']
        for wizard in self:
            wizard.brand_attribute_id = attribute

    @api.constrains('ean', 'upc', 'asin', 'description', 'additional_question')
    def _check_input(self):
        """Require at least one identifier, description, or follow-up question."""
        for wizard in self:
            if not any((wizard.ean, wizard.upc, wizard.asin, wizard.description, wizard.additional_question)):
                raise ValidationError(_('Provide at least one identifier or a product description.'))

    def action_research(self):
        """Resolve local matches before calling AI, including partial conflicts."""
        self.ensure_one()
        self._check_input()
        product_model = self.env['resale.product']
        matches = []
        provided_identifiers = []
        for field_name in ('ean', 'upc', 'asin'):
            value = (getattr(self, field_name) or '').strip().upper()
            if value:
                provided_identifiers.append((field_name.upper(), value))
                product = product_model.search([(field_name, '=', value)], limit=1)
                if product:
                    matches.append((field_name.upper(), value, product))
        unique_products = {product.id: product for _, _, product in matches}
        if len(unique_products) > 1:
            found_identifiers = {(field_name, value) for field_name, value, _ in matches}
            lines = [Command.clear()]
            for field_name, value in provided_identifiers:
                product = next(
                    (item for match_field, match_value, item in matches
                     if (match_field, match_value) == (field_name, value)),
                    False,
                )
                lines.append(Command.create({
                    'identifier': '%s: %s%s' % (
                        field_name, value,
                        '' if (field_name, value) in found_identifiers else ' (not found)',
                    ),
                    'product_id': product.id if product else False,
                }))
            self.match_line_ids = lines
            self.match_conflict_message = _(
                'The supplied identifiers do not consistently identify one existing product. Review the matches below.'
            )
            self.state = 'conflict'
            return self._reload()
        if len(unique_products) == 1 and len(matches) != len(provided_identifiers):
            product = next(iter(unique_products.values()))
            for field_name, value in provided_identifiers:
                if any((match_field, match_value) == (field_name, value) for match_field, match_value, _ in matches):
                    continue
                field = field_name.lower()
                existing_value = product[field]
                conflict_type = 'mismatch' if existing_value else 'missing'
                identifier_label = '%s: %s' % (field_name, value)
                detail = (
                    _('Existing value: %s') % existing_value
                    if existing_value else _('The existing product has no %s assigned.') % field_name
                )
                self._set_partial_conflict(
                    product, field, value, existing_value, conflict_type,
                    identifier_label, detail,
                )
                return self._reload()
        if unique_products:
            self.match_existing_product_id = next(iter(unique_products.values()))
            self.state = 'matched'
            return self._reload()
        agent = self._get_agent('resale_ai_product.research_agent_id')
        if not agent:
            raise UserError(_('Configure a product research agent in Settings first.'))
        try:
            with self.env.cr.savepoint():
                result = self._ask_agent(agent)
        except ResaleAIRequestError as primary_error:
            backup = self._get_agent('resale_ai_product.backup_agent_id')
            if not backup or backup == agent:
                self.state = 'error'
                self.research_notice = _(
                    'Research agent %(agent)s (%(model)s) failed: %(error)s'
                ) % {'agent': agent.name, 'model': agent.llm_model, 'error': primary_error}
                self.ai_response = self.research_notice
                raise UserError(self.research_notice) from primary_error
            try:
                with self.env.cr.savepoint():
                    result = self._ask_agent(backup)
            except ResaleAIRequestError as backup_error:
                self.state = 'error'
                self.research_notice = _(
                    'Both research agents failed. Primary %(primary_agent)s (%(primary_model)s): %(primary)s. Backup %(backup_agent)s (%(backup_model)s): %(backup)s.'
                ) % {
                    'primary_agent': agent.name, 'primary_model': agent.llm_model,
                    'primary': primary_error, 'backup_agent': backup.name,
                    'backup_model': backup.llm_model, 'backup': backup_error,
                }
                self.ai_response = self.research_notice
                raise UserError(self.research_notice) from backup_error
            self.research_notice = _(
                'The primary research agent was unavailable. The backup research agent response is shown below.'
            )
        self._apply_result(result)
        if self.state == 'researched' and self._prepare_ai_comparison():
            return self._reload()
        return self._reload()

    def action_create_product(self):
        """Create the proposed resale product and optionally its product template."""
        self.ensure_one()
        if not self.result_name:
            raise UserError(_('Research a product and review the result before creating it.'))
        conflicts = self._identifier_conflicts(self._result_identifiers())
        if conflicts:
            self._set_database_conflict(conflicts)
            return self._reload()
        resale_product = self.env['resale.product'].create({
            'name': self.result_name,
            'description': self.result_description,
            'category_id': self.result_category_id.id or self._default_category().id,
            'ean': self.result_ean or False, 'upc': self.result_upc or False, 'asin': self.result_asin or False,
            'reference_retail_price': self.result_retail_price, 'launch_year': self.result_launch_year or False,
            'brand_value_id': self.result_brand_value_id.id or False,
        })
        for lang in self.env['res.lang'].search([('active', '=', True)]).mapped('code'):
            name = self.with_context(lang=lang).result_name
            description = self.with_context(lang=lang).result_description
            translated_values = {
                field_name: value for field_name, value in {
                    'name': name,
                    'description': description,
                }.items() if value
            }
            if translated_values:
                resale_product.with_context(lang=lang).write(translated_values)
        return self._open_or_create_template(resale_product)

    def action_open_existing(self):
        self.ensure_one()
        if not self.match_existing_product_id:
            raise UserError(_('No existing product was matched.'))
        return self._open_or_create_template(self.match_existing_product_id)

    def _open_or_create_template(self, resale_product):
        if self.from_template:
            return resale_product.action_create_product()
        return self._open_existing_product(resale_product)

    def action_apply_ai_to_existing(self):
        self.ensure_one()
        if not self.comparison_target_product_id:
            raise UserError(_('Select an existing product before applying the AI proposal.'))
        conflicts = self._identifier_conflicts(
            self._result_identifiers(), exclude_product=self.comparison_target_product_id,
        )
        if conflicts:
            self._set_database_conflict(conflicts)
            return self._reload()
        target = self.comparison_target_product_id
        values = {
            'name': self.result_name,
            'description': self.result_description,
            'category_id': self.result_category_id.id,
            'brand_value_id': self.result_brand_value_id.id,
            'ean': self.result_ean,
            'upc': self.result_upc,
            'asin': self.result_asin,
            'reference_retail_price': self.result_retail_price,
            'launch_year': self.result_launch_year,
        }
        values = {
            field_name: value for field_name, value in values.items()
            if value not in (False, None, '', 0)
        }
        target.write(values)
        for lang in self.env['res.lang'].search([('active', '=', True)]).mapped('code'):
            name = self.with_context(lang=lang).result_name
            description = self.with_context(lang=lang).result_description
            translated_values = {
                field_name: value for field_name, value in {
                    'name': name,
                    'description': description,
                }.items() if value
            }
            if translated_values:
                target.with_context(lang=lang).write(translated_values)
        return self._open_or_create_template(target)

    def _get_agent(self, key):
        return self.env['resale.ai.service'].get_agent(key)

    def _result_identifiers(self):
        return {
            field_name: (getattr(self, 'result_%s' % field_name) or '').strip().upper()
            for field_name in ('ean', 'upc', 'asin')
        }

    def _identifier_conflicts(self, identifiers, exclude_product=None):
        """Find existing records that claim any supplied identifier."""
        conflicts = self.env['resale.product']
        for field_name, value in identifiers.items():
            if not value:
                continue
            matches = self.env['resale.product'].search([(field_name, '=', value)])
            conflicts |= matches.filtered(lambda product: not exclude_product or product != exclude_product)
        return conflicts

    def _prepare_ai_comparison(self):
        matches = []
        for field_name, value in self._result_identifiers().items():
            if value:
                product = self.env['resale.product'].search([(field_name, '=', value)], limit=1)
                if product:
                    matches.append(product)
        products = self.env['resale.product'].browse({product.id for product in matches})
        if not products:
            return False
        values = [
            ('Name (%s)' % lang, self.with_context(lang=lang).result_name, 'name', lang)
            for lang in self.env['res.lang'].search([('active', '=', True)]).mapped('code')
        ] + [
            ('Description (%s)' % lang, self.with_context(lang=lang).result_description, 'description', lang)
            for lang in self.env['res.lang'].search([('active', '=', True)]).mapped('code')
        ] + [
            ('Category', self.result_category_id.display_name, 'category_id', False),
            ('Brand', self.result_brand_value_id.display_name, 'brand_value_id', False),
            ('EAN', self.result_ean, 'ean', False),
            ('UPC', self.result_upc, 'upc', False),
            ('ASIN', self.result_asin, 'asin', False),
            ('Reference price', self.result_retail_price, 'reference_retail_price', False),
            ('Launch year', self.result_launch_year, 'launch_year', False),
        ]
        lines = [Command.clear()]
        for field_label, ai_value, field_name, lang in values:
            line_values = {
                'field_label': field_label,
                'ai_value': str(ai_value or ''),
            }
            for index, product in enumerate(products[:3]):
                suffix = chr(ord('a') + index)
                product_values = {
                    'name': product.with_context(lang=lang).name if lang else product.name,
                    'description': product.with_context(lang=lang).description if lang else product.description,
                    'category_id': product.category_id.display_name,
                    'brand_value_id': product.brand_value_id.display_name,
                    'ean': product.ean,
                    'upc': product.upc,
                    'asin': product.asin,
                    'reference_retail_price': product.reference_retail_price,
                    'launch_year': product.launch_year,
                }
                line_values['product_%s_value' % suffix] = str(product_values[field_name] or '')
            lines.append(Command.create(line_values))
        self.comparison_ids = lines
        self.comparison_product_ids = [Command.set(products.ids)]
        if len(products) == 1:
            self.comparison_target_product_id = products
        self.match_conflict_message = _(
            'The AI proposal contains an identifier already present in the database. Review the read-only comparison and edit the AI proposal before creating or applying it.'
        )
        self.state = 'comparison'
        return True

    def _set_database_conflict(self, products):
        self._prepare_ai_comparison()
        self.comparison_product_ids = [Command.set(products.ids)]
        self.comparison_target_product_id = products if len(products) == 1 else False
        self.match_conflict_message = _(
            'The edited identifiers are still used by existing products. Review the comparison and remove or change the conflicting values.'
        )
        self.state = 'comparison'

    def _set_partial_conflict(self, product, field, supplied_value, existing_value, conflict_type, identifier_label, detail):
        self.match_line_ids = [Command.clear(), Command.create({
            'identifier': '%s (%s)' % (identifier_label, detail), 'product_id': product.id,
        })]
        self.conflict_product_id = product
        self.conflict_field = field
        self.conflict_supplied_value = supplied_value
        self.conflict_existing_value = existing_value or False
        self.conflict_type = conflict_type
        self.match_conflict_message = _(
            'The supplied %(identifier)s does not match the existing product. Choose how to handle it.'
        ) % {'identifier': identifier_label}
        self.state = 'conflict'

    def _resolve_partial_conflict(self, replace):
        self.ensure_one()
        if replace:
            self.conflict_product_id.write({self.conflict_field: self.conflict_supplied_value})
        return self._open_existing_product(self.conflict_product_id)

    def action_keep_existing_identifier(self):
        return self._resolve_partial_conflict(False)

    def action_replace_identifier(self):
        return self._resolve_partial_conflict(True)

    def action_save_identifier(self):
        return self._resolve_partial_conflict(True)

    def action_skip_identifier(self):
        return self._resolve_partial_conflict(False)

    def _open_existing_product(self, product):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Resale Product'),
            'res_model': 'resale.product',
            'res_id': product.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _default_category(self):
        value = self.env['ir.config_parameter'].sudo().get_param('resale_ai_product.default_category_id')
        category = self.env['product.category'].browse(int(value)).exists() if value and value.isdigit() else self.env['product.category']
        return category.filtered('category_code')

    def _ask_agent(self, agent):
        """Request structured product data using the configured research agent."""
        categories = self.env['product.category'].search([('category_code', '!=', False)])
        brand_id = self.env['ir.config_parameter'].sudo().get_param('resale_attributes.brand_attribute_id', '0')
        brand_attribute = self.env['product.attribute'].browse(int(brand_id)).exists() if brand_id.isdigit() else self.env['product.attribute']
        brands = brand_attribute.value_ids if brand_attribute else self.env['product.attribute.value']
        languages = self.env['res.lang'].search([('active', '=', True)]).mapped('code')
        schema = {'type': 'object', 'properties': {
            'needs_details': {'type': 'boolean'}, 'question': {'type': 'string'}, 'names': {'type': 'object', 'additionalProperties': {'type': 'string'}},
            'category_code': {'type': 'string'}, 'brand': {'type': 'string'}, 'ean': {'type': 'string'}, 'upc': {'type': 'string'}, 'asin': {'type': 'string'},
            'retail_price': {'type': 'number'}, 'launch_year': {'type': 'integer'},
        }, 'required': ['needs_details', 'question', 'names', 'category_code', 'brand', 'ean', 'upc', 'asin', 'retail_price', 'launch_year']}
        if not self.exclude_description:
            schema['properties']['descriptions'] = {'type': 'object', 'additionalProperties': {'type': 'string'}}
            schema['required'].insert(3, 'descriptions')
        description_template = '' if self.exclude_description else '  "descriptions": {"en_US": "Concise product description in English"},\n'
        description_rule = (
            'Do not return a descriptions field.' if self.exclude_description else
            'Descriptions must contain every installed language code and should be accurate and concise.'
        )
        prompt = _('''Research this product using web search. Never invent identifiers or prices. If input is insufficient, set needs_details=true and ask one concise question. Otherwise return all fields.
Return ONLY one valid JSON object. Do not return Markdown fences, comments, explanations, or any other text. If available return MSRP as a "retail_price".
Use this exact response template and key names:
{
  "needs_details": false,
  "question": "",
  "names": {"en_US": "Product name in English"},
%(description_template)s  "category_code": "01",
  "brand": "Apple",
  "ean": "0190199098534",
  "upc": "190199098534",
  "asin": null,
  "retail_price": 0.0,
  "launch_year": null
}
Rules: names must contain every installed language code and each name must be 50 characters or fewer. %(description_rule)s Use only an allowed category_code. Use only an allowed brand, or an empty string when unknown. Use null for an unknown identifier, price, or launch year. When needs_details is true, put the single clarification question in question and still include every other template key.
EAN: %(ean)s
UPC: %(upc)s
ASIN: %(asin)s
Description: %(description)s
Additional answer: %(answer)s
Allowed categories (code: name): %(categories)s
Allowed brands: %(brands)s
Installed language codes: %(languages)s''') % {
            'ean': self.ean or '', 'upc': self.upc or '', 'asin': self.asin or '',
            'description': self.description or '',
            'answer': self.additional_question or '',
            'categories': ', '.join('%s: %s' % (c.category_code, c.display_name) for c in categories), 'brands': ', '.join(brands.mapped('name')), 'languages': ', '.join(languages),
            'description_template': description_template, 'description_rule': description_rule}
        response = self.env['resale.ai.service'].request_llm(
            agent,
            [agent.system_prompt or 'You are a careful product research agent researching primarily Spanish market, if you dont find enough relevant information then European. If neither of those results in satisfactory result then search globally.'],
            [prompt],
            schema=schema,
            service_class=ResearchLLMApiService,
        )
        raw = response[-1] if response else ''
        self.ai_response = raw
        try:
            return self.env['resale.ai.service'].parse_json_response(response)
        except (TypeError, ValueError) as error:
            raise UserError(_('The AI agent returned an invalid structured response.')) from error

    def _apply_result(self, result):
        """Normalize and present the AI result for operator review."""
        if result.get('needs_details'):
            self.ai_question, self.state = result.get('question') or _('Please provide more details.'), 'question'
            return
        category_code = result.get('category_code')
        category = self.env['product.category'].search([('category_code', '=', category_code)], limit=1) if category_code else self.env['product.category']
        if not category and result.get('category_id'):
            category = self.env['product.category'].browse(result['category_id']).filtered('category_code')
        self.result_category_id = category or self._default_category()
        self.result_brand_value_id = self._brand_value((result.get('brand') or '').strip()) or self._default_brand()
        self.result_ean, self.result_upc, self.result_asin = result.get('ean') or False, result.get('upc') or False, result.get('asin') or False
        self.result_retail_price, self.result_launch_year = result.get('retail_price') or 0, result.get('launch_year') or False
        names = result.get('names') or result.get('name') or {}
        if isinstance(names, str):
            names = {self.env.lang or 'en_US': names}
        languages = self.env['res.lang'].search([('active', '=', True)]).mapped('code')
        fallback_name = next((str(name).strip()[:50] for name in names.values() if name), '')
        preview = []
        for lang in languages:
            name = (names.get(lang) or names.get(lang.split('_')[0]) or fallback_name).strip()[:50]
            if name:
                self.with_context(lang=lang).result_name = name
                preview.append('%s: %s' % (lang, name))
        self.translation_preview = '\n'.join(preview)
        descriptions = {} if self.exclude_description else result.get('descriptions') or result.get('description') or {}
        if isinstance(descriptions, str):
            descriptions = {self.env.lang or 'en_US': descriptions}
        description_fallback = next((str(value).strip() for value in descriptions.values() if value), '')
        description_preview = []
        for lang in languages:
            description = (descriptions.get(lang) or descriptions.get(lang.split('_')[0]) or description_fallback).strip()
            if description:
                self.with_context(lang=lang).result_description = description
                description_preview.append('%s: %s' % (lang, description))
        self.description_translation_preview = '\n'.join(description_preview)
        if fallback_name and not self.result_name:
            self.result_name = fallback_name
        if not self.result_name:
            raise UserError(_('The AI agent did not return a product name.'))
        self.state = 'researched'

    def _brand_value(self, name):
        attribute = self._brand_attribute()
        return self.env['product.attribute.value'].search([('name', '=ilike', name), ('attribute_id', '=', attribute.id)], limit=1) if name and attribute else self.env['product.attribute.value']

    def _default_brand(self):
        value = self.env['ir.config_parameter'].sudo().get_param('resale_ai_product.default_brand_value_id')
        brand = self.env['product.attribute.value'].browse(int(value)).exists() if value and value.isdigit() else self.env['product.attribute.value']
        return brand.filtered(lambda item: item.attribute_id == self._brand_attribute())

    def _brand_attribute(self):
        value = self.env['ir.config_parameter'].sudo().get_param('resale_attributes.brand_attribute_id')
        return self.env['product.attribute'].browse(int(value)).exists() if value and value.isdigit() else self.env['product.attribute']

    def _reload(self):
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id, 'view_mode': 'form', 'target': 'new'}
