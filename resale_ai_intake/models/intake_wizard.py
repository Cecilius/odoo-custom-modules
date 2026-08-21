import json
import ipaddress
import re
import socket
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResaleAIIntakeWizard(models.TransientModel):
    _name = 'resale.ai.intake.wizard'
    _description = 'Resale AI Item Intake'

    batch_id = fields.Many2one('resale.acquisition.batch', required=True)
    identifier = fields.Char(string='Lookup Identifier', readonly=True)
    input_ean = fields.Char(string='Last EAN', readonly=True)
    input_upc = fields.Char(string='Last UPC', readonly=True)
    input_asin = fields.Char(string='Last ASIN', readonly=True)
    input_search_text = fields.Char(string='Last Product Search', readonly=True)
    identifier_type = fields.Selection([
        ('ean', 'EAN / UPC'),
        ('asin', 'ASIN'),
    ], default='ean', required=True)
    state = fields.Selection([
        ('input', 'Input'),
        ('review', 'Review'),
        ('error', 'Error'),
    ], default='input')
    result_name = fields.Char(string='Suggested Product Name')
    result_model = fields.Char(string='Suggested Model')
    result_brand_name = fields.Char(string='Suggested Brand')
    brand_value_id = fields.Many2one(
        'product.attribute.value',
        string='Brand',
        domain="[('resale_is_brand', '=', True)]",
    )
    category_id = fields.Many2one('product.category', string='Suggested Category')
    result_category_path = fields.Char(string='AI Category Path', readonly=True)
    result_asin = fields.Char(string='ASIN')
    result_ean = fields.Char(string='EAN')
    result_upc = fields.Char(string='UPC')
    current_price = fields.Monetary(currency_field='currency_id')
    lowest_price_180 = fields.Monetary(
        string='Lowest Price (180 days)', currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id, readonly=True,
    )
    confidence = fields.Float(readonly=True)
    sources = fields.Text(readonly=True)
    raw_response = fields.Text(readonly=True)
    raw_agent_response = fields.Text(
        string='Raw AI Response',
        readonly=True,
        help='Exact response returned by the selected native Odoo AI agent.',
    )
    agent_id = fields.Many2one('ai.agent', string='Agent Used', readonly=True)
    error_message = fields.Text(readonly=True)
    follow_up_questions = fields.Text(string='Additional Questions', readonly=True)
    follow_up_answers = fields.Text(string='Answers')
    identifier_verification = fields.Text(string='Identifier Verification', readonly=True)
    name_line_ids = fields.One2many(
        'resale.ai.name.line', 'wizard_id', string='Translated Names',
    )
    item_count = fields.Integer(compute='_compute_item_count')
    planned_rfb = fields.Char(string='Planned RFB', compute='_compute_rfb_preview')
    last_rfb = fields.Char(string='Last Assigned RFB', readonly=True)
    last_product_id = fields.Many2one('product.product', string='Last Created Item', readonly=True)
    changed_fields = fields.Char(string='Changed by User', compute='_compute_changed_fields')
    ai_suggested_name = fields.Char(copy=False)
    ai_suggested_model = fields.Char(copy=False)
    ai_suggested_brand_name = fields.Char(copy=False)
    ai_suggested_brand_value_id = fields.Many2one('product.attribute.value', copy=False)
    ai_suggested_category_id = fields.Many2one('product.category', copy=False)
    ai_suggested_asin = fields.Char(copy=False)
    ai_suggested_ean = fields.Char(copy=False)
    ai_suggested_upc = fields.Char(copy=False)
    ai_suggested_current_price = fields.Monetary(currency_field='currency_id', copy=False)
    ai_suggested_lowest_price_180 = fields.Monetary(currency_field='currency_id', copy=False)

    @api.depends('batch_id.item_ids')
    def _compute_item_count(self):
        for wizard in self:
            wizard.item_count = len(wizard.batch_id.item_ids)

    @api.depends('category_id')
    def _compute_rfb_preview(self):
        for wizard in self:
            if wizard.category_id:
                wizard.category_id._synchronize_rfb_sequence()
            sequence = wizard.category_id.rfb_sequence_id
            if wizard.category_id.rfb_prefix and sequence:
                next_number = getattr(sequence, 'number_next_actual', sequence.number_next)
                wizard.planned_rfb = f'RFB-{wizard.category_id.rfb_prefix}-{next_number:06d}'
            else:
                wizard.planned_rfb = False

    @api.depends(
        'result_name', 'result_model', 'result_brand_name', 'brand_value_id',
        'category_id', 'result_asin', 'result_ean', 'current_price',
        'lowest_price_180', 'ai_suggested_name', 'ai_suggested_model',
        'ai_suggested_brand_name', 'ai_suggested_brand_value_id',
        'ai_suggested_category_id', 'ai_suggested_asin', 'ai_suggested_ean',
        'ai_suggested_upc',
        'ai_suggested_current_price', 'ai_suggested_lowest_price_180',
    )
    def _compute_changed_fields(self):
        for wizard in self:
            changed = []
            comparisons = [
                ('Name', wizard.result_name, wizard.ai_suggested_name),
                ('Model', wizard.result_model, wizard.ai_suggested_model),
                ('Brand', wizard.brand_value_id, wizard.ai_suggested_brand_value_id),
                ('Brand Name', wizard.result_brand_name, wizard.ai_suggested_brand_name),
                ('Category', wizard.category_id, wizard.ai_suggested_category_id),
                ('ASIN', wizard.result_asin, wizard.ai_suggested_asin),
                ('EAN / UPC', wizard.result_ean, wizard.ai_suggested_ean),
                ('UPC', wizard.result_upc, wizard.ai_suggested_upc),
                ('Current Price', wizard.current_price, wizard.ai_suggested_current_price),
                ('Lowest Price', wizard.lowest_price_180, wizard.ai_suggested_lowest_price_180),
            ]
            for label, current, original in comparisons:
                current_id = current.id if hasattr(current, 'id') else current
                original_id = original.id if hasattr(original, 'id') else original
                if current_id != original_id:
                    changed.append(label)
            wizard.changed_fields = ', '.join(changed) or 'None'

    @api.model
    def _normalize(self, value):
        return re.sub(r'[^a-z0-9]+', ' ', (value or '').lower()).strip()

    @api.model
    def _parse_response(self, response):
        text = '\n'.join(response or []).strip()
        if '```' in text:
            text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.S).strip()
        start, end = text.find('{'), text.rfind('}')
        if start < 0 or end <= start:
            raise UserError(_('The AI response did not contain a JSON object.'))
        try:
            result = json.loads(text[start:end + 1])
        except json.JSONDecodeError as error:
            raise UserError(_('The AI response was not valid JSON: %s') % error)
        if not isinstance(result, dict):
            raise UserError(_('The AI response must be a JSON object.'))
        return result

    @api.model
    def _normalize_identifier(self, value):
        return re.sub(r'[^a-z0-9]', '', (value or '').lower())

    @api.model
    def _safe_source_text(self, url):
        parsed = urlparse(url or '')
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            return ''
        try:
            addresses = {
                info[4][0]
                for info in socket.getaddrinfo(parsed.hostname, None)
            }
            if any(ipaddress.ip_address(address).is_private for address in addresses):
                return ''
            request = Request(
                url,
                headers={'User-Agent': 'Odoo Resale AI Intake/1.0'},
            )
            with urlopen(request, timeout=8) as response:
                return response.read(2_000_000).decode('utf-8', errors='ignore')
        except Exception:
            return ''

    def _identifier_has_source_evidence(self, identifier, sources):
        normalized = self._normalize_identifier(identifier)
        if not normalized:
            return False
        for source in sources or []:
            url = source.get('url') if isinstance(source, dict) else False
            page = self._safe_source_text(url)
            if self._normalize_identifier(normalized) in self._normalize_identifier(page):
                return True
        return False

    @api.model
    def _identifier_format_is_valid(self, field_name, value):
        normalized = self._normalize_identifier(value)
        if field_name == 'ean':
            return normalized.isdigit() and len(normalized) in (8, 13)
        if field_name == 'upc':
            return normalized.isdigit() and len(normalized) == 12
        if field_name == 'asin':
            return bool(re.fullmatch(r'[A-Z0-9]{10}', normalized.upper()))
        return False

    def _sanitize_identifiers(self, result, sources):
        result = dict(result)
        messages = []
        for field_name, supplied in (
            ('ean', self.input_ean),
            ('upc', self.input_upc),
            ('asin', self.input_asin),
        ):
            candidate = result.get(field_name)
            if supplied:
                result[field_name] = supplied
                continue
            if candidate and not self._identifier_format_is_valid(field_name, candidate):
                result[field_name] = None
                messages.append(f'{field_name.upper()} returned by AI has the wrong format.')
            elif candidate and not self._identifier_has_source_evidence(candidate, sources):
                result[field_name] = None
                messages.append(
                    f'{field_name.upper()} returned by AI but not verified in a source page.'
                )
        return result, messages

    def _category_options(self):
        root = self.env.ref('resale.product_category_resale')
        return '\n'.join(
            f'{category.id}: {category.complete_name}'
            for category in self.env['product.category'].search([
                ('id', 'child_of', root.id),
                ('rfb_prefix', '!=', False),
            ], order='complete_name')
        )

    def _brand_options(self):
        return '\n'.join(
            f'{brand.id}: {brand.name}'
            for brand in self.env['product.attribute.value'].search([
                ('resale_is_brand', '=', True),
            ], order='name')
        )

    def _active_language_options(self):
        return '\n'.join(
            f'{language.code}: {language.name}'
            for language in self.env['res.lang'].search([('active', '=', True)], order='code')
        )

    def _prompt(self, deep=False, secondary=False, follow_up_answers=None):
        task = 'deeply research' if deep else 'identify'
        if secondary:
            task = 'normalize the brand and category match'
        return f"""
You {task} one product for an Odoo resale intake workflow.
        EAN: {self.input_ean or 'not provided'}
        UPC: {self.input_upc or 'not provided'}
        ASIN: {self.input_asin or 'not provided'}
        Product search text: {self.input_search_text or 'not provided'}

Existing resale categories (return one exact category id when possible):
{self._category_options()}

Existing brands (prefer an exact existing brand id when possible):
{self._brand_options()}

Active languages for product names:
{self._active_language_options()}

Return JSON only, with this schema:
{{
  "identifier_verified": true,
  "name": null,
  "names": {{}},
  "model": null,
  "brand": null,
  "matched_brand_id": null,
  "asin": null,
  "ean": null,
  "upc": null,
  "category_id": null,
  "category_path": null,
  "current_retail_price": null,
  "lowest_price_180_days": null,
  "currency": "EUR",
  "confidence": 0.0,
  "sources": [{{"url": "", "claim": ""}}],
  "follow_up_questions": [],
  "reason": ""
}}

EAN is normally 13 digits; UPC-A is normally 12 digits. Keep them in their
correct fields and never use a UPC as an EAN. If an EAN, UPC, or ASIN was not
supplied, use the product search text to find and verify it from reliable sources.
For ASIN searches, check Amazon Spain and other European marketplaces including
amazon.es, amazon.co.uk, amazon.de, amazon.fr, amazon.it, and amazon.nl.
Never invent an identifier, price, source, or
category id. Use null when unknown.
Keep the product name at 40 characters or fewer.
If the product is still ambiguous, return up to three concise follow_up_questions
that would help distinguish it. If it is sufficiently identified, return an empty
array. Questions must be answerable from packaging, photos, or the operator.
Follow-up answers from the operator:
{follow_up_answers or 'none'}
Verify that the supplied identifier appears in a source. Historical price must be
left null unless the source supports it. {"Use multiple sources and investigate disagreements." if deep else "Use concise source-backed lookup."}
"""

    def _call_agent(self, agent, deep=False, secondary=False, follow_up_answers=None):
        if not agent:
            raise UserError(_('No AI agent is configured for this task.'))
        response = agent.get_direct_response(
            self._prompt(
                deep=deep,
                secondary=secondary,
                follow_up_answers=follow_up_answers,
            ),
            context_message='Return strict JSON only. Do not use markdown.',
        )
        self.raw_agent_response = '\n'.join(response or [])
        return self._parse_response(response)

    def _find_brand(self, result):
        if result.get('matched_brand_id'):
            brand = self.env['product.attribute.value'].browse(int(result['matched_brand_id']))
            if brand.exists() and brand.resale_is_brand:
                return brand
        normalized = self._normalize(result.get('brand'))
        return self.env['product.attribute.value'].search([
            ('resale_is_brand', '=', True),
        ], order='name').filtered(
            lambda brand: self._normalize(brand.name) == normalized
        )[:1]

    def _apply_result(self, result, agent, fields_to_update=None):
        fields_to_update = set(fields_to_update or {
            'name', 'model', 'brand', 'category', 'asin', 'ean',
            'current_price', 'lowest_price_180',
        })
        category = self.env['product.category']
        if result.get('category_id'):
            category = self.env['product.category'].browse(int(result['category_id']))
            if not category.exists() or not category.rfb_prefix:
                category = self.env['product.category']
        brand = self._find_brand(result)
        sources = result.get('sources') or []
        result, verification_messages = self._sanitize_identifiers(result, sources)
        names = result.get('names') or {}
        if not isinstance(names, dict):
            names = {}
        base_name = (result.get('name') or '')[:40]
        self.name_line_ids.unlink()
        name_lines = []
        for language in self.env['res.lang'].search([('active', '=', True)], order='code'):
            translated = (names.get(language.code) or base_name)[:40]
            name_lines.append((0, 0, {
                'lang_code': language.code,
                'language_name': language.name,
                'name': translated,
                'ai_name': translated,
            }))
        values = {
            'state': 'review',
            'confidence': result.get('confidence') or 0.0,
            'sources': json.dumps(sources, ensure_ascii=True, indent=2),
            'raw_response': json.dumps(result, ensure_ascii=True, indent=2),
            'agent_id': agent.id,
            'error_message': False,
            'name_line_ids': name_lines,
            'identifier_verification': '\n'.join(verification_messages) or 'All returned identifiers verified or supplied by user.',
        }
        if 'follow_up_questions' in result:
            questions = list(result.get('follow_up_questions') or [])
            questions.extend(verification_messages)
            values['follow_up_questions'] = '\n'.join(
                f'- {question}'
                for question in questions
            )
        field_map = {
            'name': (
                'result_name', 'ai_suggested_name',
                (result.get('name') or '')[:40],
            ),
            'model': ('result_model', 'ai_suggested_model', result.get('model')),
            'brand': ('result_brand_name', 'ai_suggested_brand_name', result.get('brand')),
            'category': ('category_id', 'ai_suggested_category_id', category.id or False),
            'asin': ('result_asin', 'ai_suggested_asin', result.get('asin')),
            'ean': ('result_ean', 'ai_suggested_ean', result.get('ean')),
            'upc': ('result_upc', 'ai_suggested_upc', result.get('upc')),
            'current_price': (
                'current_price', 'ai_suggested_current_price',
                result.get('current_retail_price'),
            ),
            'lowest_price_180': (
                'lowest_price_180', 'ai_suggested_lowest_price_180',
                result.get('lowest_price_180_days'),
            ),
        }
        for field_name in fields_to_update:
            if field_name not in field_map:
                continue
            result_field, suggested_field, value = field_map[field_name]
            if value is None:
                continue
            values[result_field] = value
            values[suggested_field] = value
        if 'brand' in fields_to_update and result.get('brand') is not None:
            values['brand_value_id'] = brand.id or False
        if 'category' in fields_to_update and result.get('category_path') is not None:
            values['result_category_path'] = result.get('category_path')
        self.write(values)
        return result

    def action_open_identifier_popup(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'AI Product Lookup',
            'res_model': 'resale.ai.lookup.input.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_parent_wizard_id': self.id},
        }

    def action_open_research_popup(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'AI Research Fields',
            'res_model': 'resale.ai.research.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_parent_wizard_id': self.id},
        }

    def action_lookup_from_identifiers(self, ean=False, upc=False, asin=False, search_text=False):
        self.ensure_one()
        if not ean and not upc and not asin and not search_text:
            raise UserError(_('Enter an EAN, UPC, ASIN, or product search text before starting the lookup.'))
        self.write({
            'input_ean': ean or False,
            'input_upc': upc or False,
            'input_asin': asin or False,
            'input_search_text': search_text or False,
            'identifier': asin or ean or upc or search_text,
        })
        return self._run_lookup()

    def _run_lookup(self):
        self.ensure_one()
        configuration = self.env['resale.ai.configuration'].get_default()
        try:
            result = self._call_agent(configuration.primary_agent_id)
            self._apply_result(result, configuration.primary_agent_id)
            if (
                configuration.automatic_fallback
                and result.get('confidence', 0.0) < configuration.confidence_threshold
                and configuration.fallback_agent_id
            ):
                result = self._call_agent(configuration.fallback_agent_id, deep=True)
                self._apply_result(result, configuration.fallback_agent_id)
        except Exception as error:
            self.write({'state': 'error', 'error_message': str(error)})
        return self._reload_action()

    def action_lookup(self):
        return self.action_open_identifier_popup()

    def action_reset_input(self):
        self.ensure_one()
        self.write({
            'state': 'input',
            'error_message': False,
            'raw_agent_response': False,
        })
        return self._reload_action()

    def action_deep_research(self):
        return self.action_open_research_popup()

    def action_secondary_review(self):
        return self.action_open_research_popup()

    def action_research_selected(self, selected_fields, role='deep'):
        self.ensure_one()
        configuration = self.env['resale.ai.configuration'].get_default()
        try:
            secondary = role == 'secondary'
            agent = configuration.secondary_agent_id if secondary else configuration.fallback_agent_id
            result = self._call_agent(agent, deep=not secondary, secondary=secondary)
            self._apply_result(result, agent, selected_fields)
        except Exception as error:
            self.write({'state': 'error', 'error_message': str(error)})
        return self._reload_action()

    def action_research_with_answers(self):
        self.ensure_one()
        if not self.follow_up_answers:
            raise UserError(_('Enter at least one answer before researching again.'))
        configuration = self.env['resale.ai.configuration'].get_default()
        try:
            result = self._call_agent(
                configuration.fallback_agent_id,
                deep=True,
                follow_up_answers=self.follow_up_answers,
            )
            self._apply_result(result, configuration.fallback_agent_id)
        except Exception as error:
            self.write({'state': 'error', 'error_message': str(error)})
        return self._reload_action()

    def action_confirm_next(self):
        self.ensure_one()
        if self.state != 'review' or not self.result_name:
            raise UserError(_('Run a lookup and review the result before confirming.'))
        if not self.category_id:
            raise UserError(_('Select or confirm a resale category before creating the item.'))
        if not self.category_id.rfb_prefix:
            raise UserError(_('Select a leaf resale category with an RFB prefix.'))
        brand = self.brand_value_id
        if self.result_brand_name and (
            not brand
            or self._normalize(brand.name) != self._normalize(self.result_brand_name)
        ):
            brand = self.env['product.attribute.value'].search([
                ('resale_is_brand', '=', True),
            ], order='name').filtered(
                lambda item: self._normalize(item.name) == self._normalize(self.result_brand_name)
            )[:1]
            if not brand:
                brand = self.env['product.attribute.value'].create({
                    'name': self.result_brand_name,
                    'attribute_id': self.env.ref('resale.product_attribute_brand').id,
                    'resale_is_brand': True,
                })
        created_values = {
            'name': self.result_name,
            'categ_id': self.category_id.id,
            'batch_id': self.batch_id.id,
            'brand_value_id': brand.id or False,
            'asin': self.result_asin or self.input_asin,
            'ean': self.result_ean or self.input_ean,
            'upc': self.result_upc or self.input_upc,
            'recommended_price': self.lowest_price_180 or self.current_price,
            'initial_value': self.lowest_price_180 or self.current_price,
            'ai_lookup_agent_id': self.agent_id.id,
            'ai_lookup_date': fields.Datetime.now(),
            'ai_lookup_confidence': self.confidence,
            'ai_lookup_identifier': self.input_asin or self.input_ean or self.input_upc or self.identifier,
            'ai_lookup_sources': self.sources,
            'ai_lookup_raw': self.raw_response,
            'ai_retail_price_current': self.current_price,
            'ai_retail_price_low_180': self.lowest_price_180,
            'ai_user_changed_fields': self.changed_fields,
            'ai_follow_up_questions': self.follow_up_questions,
            'ai_follow_up_answers': self.follow_up_answers,
            'ai_identifier_verification': self.identifier_verification,
        }
        product = self.env['product.product'].create(created_values)
        translations = {}
        for line in self.name_line_ids:
            if line.name:
                translations[line.lang_code] = line.name
                product.with_context(lang=line.lang_code).write({'name': line.name})
        if translations:
            product.ai_name_translations = json.dumps(translations, ensure_ascii=True)
        self.write({
            'last_rfb': product.rfb,
            'last_product_id': product.id,
            'identifier': False,
            'input_ean': False,
            'input_upc': False,
            'input_asin': False,
            'input_search_text': False,
            'state': 'input',
            'result_name': False,
            'result_model': False,
            'result_brand_name': False,
            'brand_value_id': False,
            'category_id': False,
            'result_category_path': False,
            'result_asin': False,
            'result_ean': False,
            'result_upc': False,
            'current_price': 0.0,
            'lowest_price_180': 0.0,
            'confidence': 0.0,
            'sources': False,
            'raw_response': False,
            'raw_agent_response': False,
            'agent_id': False,
            'error_message': False,
            'follow_up_questions': False,
            'follow_up_answers': False,
            'name_line_ids': [(5, 0, 0)],
            'ai_suggested_name': False,
            'ai_suggested_model': False,
            'ai_suggested_brand_name': False,
            'ai_suggested_brand_value_id': False,
            'ai_suggested_category_id': False,
            'ai_suggested_asin': False,
            'ai_suggested_ean': False,
            'ai_suggested_upc': False,
            'ai_suggested_current_price': 0.0,
            'ai_suggested_lowest_price_180': 0.0,
        })
        return self._reload_action()

    def _reload_action(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
