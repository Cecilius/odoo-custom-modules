import json
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResaleAIIntakeWizard(models.TransientModel):
    _name = 'resale.ai.intake.wizard'
    _description = 'Resale AI Item Intake'

    batch_id = fields.Many2one('resale.acquisition.batch', required=True)
    identifier = fields.Char(string='EAN / ASIN', required=True)
    identifier_type = fields.Selection([
        ('ean', 'EAN / UPC'),
        ('asin', 'ASIN'),
    ], default='ean', required=True)
    state = fields.Selection([
        ('input', 'Input'),
        ('review', 'Review'),
        ('error', 'Error'),
    ], default='input')
    result_name = fields.Char(string='Suggested Product Name', readonly=True)
    result_model = fields.Char(string='Suggested Model', readonly=True)
    result_brand_name = fields.Char(string='Suggested Brand', readonly=True)
    brand_id = fields.Many2one('resale.brand', string='Brand')
    category_id = fields.Many2one('product.category', string='Suggested Category')
    result_category_path = fields.Char(string='AI Category Path', readonly=True)
    result_asin = fields.Char(string='ASIN', readonly=True)
    result_ean = fields.Char(string='EAN / UPC', readonly=True)
    current_price = fields.Monetary(currency_field='currency_id', readonly=True)
    lowest_price_180 = fields.Monetary(
        string='Lowest Price (180 days)', currency_field='currency_id', readonly=True,
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
    item_count = fields.Integer(compute='_compute_item_count')

    @api.depends('batch_id.item_ids')
    def _compute_item_count(self):
        for wizard in self:
            wizard.item_count = len(wizard.batch_id.item_ids)

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

    def _category_options(self):
        root = self.env.ref('resale.product_category_resale')
        return '\n'.join(
            f'{category.id}: {category.complete_name}'
            for category in self.env['product.category'].search([
                ('id', 'child_of', root.id),
            ], order='complete_name')
        )

    def _brand_options(self):
        return '\n'.join(
            f'{brand.id}: {brand.name}'
            for brand in self.env['resale.brand'].search([], order='name')
        )

    def _prompt(self, deep=False, secondary=False):
        task = 'deeply research' if deep else 'identify'
        if secondary:
            task = 'normalize the brand and category match'
        return f"""
You {task} one product for an Odoo resale intake workflow.
Identifier type: {self.identifier_type}
Identifier: {self.identifier}

Existing resale categories (return one exact category id when possible):
{self._category_options()}

Existing brands (prefer an exact existing brand id when possible):
{self._brand_options()}

Return JSON only, with this schema:
{{
  "identifier_verified": true,
  "name": null,
  "model": null,
  "brand": null,
  "matched_brand_id": null,
  "asin": null,
  "ean": null,
  "category_id": null,
  "category_path": null,
  "current_retail_price": null,
  "lowest_price_180_days": null,
  "currency": "EUR",
  "confidence": 0.0,
  "sources": [{{"url": "", "claim": ""}}],
  "reason": ""
}}

Never invent an identifier, price, source, or category id. Use null when unknown.
Verify that the supplied identifier appears in a source. Historical price must be
left null unless the source supports it. {"Use multiple sources and investigate disagreements." if deep else "Use concise source-backed lookup."}
"""

    def _call_agent(self, agent, deep=False, secondary=False):
        if not agent:
            raise UserError(_('No AI agent is configured for this task.'))
        response = agent.get_direct_response(
            self._prompt(deep=deep, secondary=secondary),
            context_message='Return strict JSON only. Do not use markdown.',
        )
        self.raw_agent_response = '\n'.join(response or [])
        return self._parse_response(response)

    def _find_brand(self, result):
        if result.get('matched_brand_id'):
            brand = self.env['resale.brand'].browse(int(result['matched_brand_id']))
            if brand.exists():
                return brand
        normalized = self._normalize(result.get('brand'))
        return self.env['resale.brand'].search([], order='name').filtered(
            lambda brand: self._normalize(brand.name) == normalized
        )[:1]

    def _apply_result(self, result, agent):
        category = self.env['product.category'].browse(int(result['category_id'])) if result.get('category_id') else self.env['product.category']
        if category and not category.exists():
            category = self.env['product.category']
        sources = result.get('sources') or []
        self.write({
            'state': 'review',
            'result_name': result.get('name'),
            'result_model': result.get('model'),
            'result_brand_name': result.get('brand'),
            'brand_id': self._find_brand(result).id or False,
            'category_id': category.id or False,
            'result_category_path': result.get('category_path'),
            'result_asin': result.get('asin'),
            'result_ean': result.get('ean'),
            'current_price': result.get('current_retail_price') or 0.0,
            'lowest_price_180': result.get('lowest_price_180_days') or 0.0,
            'confidence': result.get('confidence') or 0.0,
            'sources': json.dumps(sources, ensure_ascii=True, indent=2),
            'raw_response': json.dumps(result, ensure_ascii=True, indent=2),
            'agent_id': agent.id,
            'error_message': False,
        })
        return result

    def action_lookup(self):
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

    def action_deep_research(self):
        self.ensure_one()
        configuration = self.env['resale.ai.configuration'].get_default()
        try:
            result = self._call_agent(configuration.fallback_agent_id, deep=True)
            self._apply_result(result, configuration.fallback_agent_id)
        except Exception as error:
            self.write({'state': 'error', 'error_message': str(error)})
        return self._reload_action()

    def action_secondary_review(self):
        self.ensure_one()
        configuration = self.env['resale.ai.configuration'].get_default()
        try:
            result = self._call_agent(configuration.secondary_agent_id, secondary=True)
            self._apply_result(result, configuration.secondary_agent_id)
        except Exception as error:
            self.write({'state': 'error', 'error_message': str(error)})
        return self._reload_action()

    def action_confirm_next(self):
        self.ensure_one()
        if self.state != 'review' or not self.result_name:
            raise UserError(_('Run a lookup and review the result before confirming.'))
        if not self.category_id:
            raise UserError(_('Select or confirm a resale category before creating the item.'))
        values = {
            'name': self.result_name,
            'categ_id': self.category_id.id,
            'batch_id': self.batch_id.id,
            'resale_brand_id': self.brand_id.id or False,
            'model_es': self.result_model,
            'asin': self.result_asin or (self.identifier if self.identifier_type == 'asin' else False),
            'upc': self.result_ean or (self.identifier if self.identifier_type == 'ean' else False),
            'recommended_price': self.lowest_price_180 or self.current_price,
            'initial_value': self.lowest_price_180 or self.current_price,
            'ai_lookup_agent_id': self.agent_id.id,
            'ai_lookup_date': fields.Datetime.now(),
            'ai_lookup_confidence': self.confidence,
            'ai_lookup_identifier': self.identifier,
            'ai_lookup_sources': self.sources,
            'ai_lookup_raw': self.raw_response,
            'ai_retail_price_current': self.current_price,
            'ai_retail_price_low_180': self.lowest_price_180,
        }
        self.env['product.product'].create(values)
        self.write({
            'identifier': False,
            'state': 'input',
            'result_name': False,
            'result_model': False,
            'result_brand_name': False,
            'brand_id': False,
            'category_id': False,
            'result_category_path': False,
            'result_asin': False,
            'result_ean': False,
            'current_price': 0.0,
            'lowest_price_180': 0.0,
            'confidence': 0.0,
            'sources': False,
            'raw_response': False,
            'raw_agent_response': False,
            'agent_id': False,
            'error_message': False,
        })
        return self._reload_action()

    def _reload_action(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
