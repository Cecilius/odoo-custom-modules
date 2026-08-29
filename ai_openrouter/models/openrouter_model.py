import logging

from odoo import _, api, fields, models

from odoo.addons.ai.utils.llm_api_service import LLMApiService


_logger = logging.getLogger(__name__)


class OpenRouterModel(models.Model):
    _name = 'ai.openrouter.model'
    _description = 'OpenRouter Model'
    _order = 'name, model_id'

    model_id = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    description = fields.Text()
    context_length = fields.Integer()
    input_modalities = fields.Char()
    output_modalities = fields.Char()
    supported_parameters = fields.Char()
    active = fields.Boolean(default=True)
    allowed = fields.Boolean(
        string='Allowed for AI agents',
        help='Only allowed models are available in the AI agent model selector.',
    )
    last_seen = fields.Datetime()
    prompt_cost_per_million = fields.Float(string='Prompt cost / 1M tokens', digits=(16, 6))
    completion_cost_per_million = fields.Float(string='Completion cost / 1M tokens', digits=(16, 6))
    request_cost = fields.Float(string='Request cost', digits=(16, 6))
    web_search_cost = fields.Float(string='Web search cost', digits=(16, 6))

    _model_id_unique = models.UniqueIndex('(model_id)')

    @api.model
    def _is_supported_model(self, model_data):
        architecture = model_data.get('architecture') or {}
        input_modalities = architecture.get('input_modalities') or []
        output_modalities = architecture.get('output_modalities') or []
        supported_parameters = model_data.get('supported_parameters') or []
        model_id = model_data.get('id') or ''

        return (
            'text' in input_modalities
            and output_modalities == ['text']
            and 'tools' in supported_parameters
            and not model_id.endswith(':batch')
        )

    @api.model
    def _fetch_models(self):
        service = LLMApiService(self.env, provider='openrouter')
        models = []
        offset = 0
        while True:
            response = service._request(
                method='get',
                endpoint='/models',
                headers=service._get_base_headers(),
                body={},
                params={
                    'output_modalities': 'text',
                    'supported_parameters': 'tools',
                    'limit': 1000,
                    'offset': offset,
                },
            )
            page = response.get('data') or []
            models.extend(page)
            if not page or not response.get('links', {}).get('next') or len(page) < 1000:
                break
            offset += len(page)
        return models

    @api.model
    def action_sync_models(self):
        """Synchronize the OpenRouter catalog into Odoo."""
        model_data = self._fetch_models()
        supported_models = [model for model in model_data if self._is_supported_model(model)]
        now = fields.Datetime.now()
        catalog = self.sudo()
        seen_ids = set()

        for model in supported_models:
            model_id = model.get('id')
            if not model_id:
                continue
            seen_ids.add(model_id)
            values = {
                'name': model.get('name') or model_id,
                'description': model.get('description'),
                'context_length': model.get('context_length') or 0,
                'input_modalities': ','.join(model.get('architecture', {}).get('input_modalities') or []),
                'output_modalities': ','.join(model.get('architecture', {}).get('output_modalities') or []),
                'supported_parameters': ','.join(model.get('supported_parameters') or []),
                'active': True,
                'last_seen': now,
                'prompt_cost_per_million': self._price_per_million(model.get('pricing', {}).get('prompt')),
                'completion_cost_per_million': self._price_per_million(model.get('pricing', {}).get('completion')),
                'request_cost': self._price_float(model.get('pricing', {}).get('request')),
                'web_search_cost': self._price_float(model.get('pricing', {}).get('web_search')),
            }
            existing = catalog.search([('model_id', '=', model_id)], limit=1)
            if existing:
                existing.write(values)
            else:
                catalog.create(dict(values, model_id=model_id))

        # An empty upstream response is treated as a failed/incomplete sync.
        # Never deactivate the entire local catalog on that basis.
        if not seen_ids:
            raise UserError(_('OpenRouter returned no compatible models; the existing catalog was left unchanged.'))

        catalog.search([('model_id', 'not in', list(seen_ids))]).write({'active': False})

        _logger.info(
            'Synchronized %s OpenRouter models; %s passed Odoo AI guardrails',
            len(model_data), len(seen_ids),
        )
        return len(seen_ids)

    @api.model
    def _price_float(self, value):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @api.model
    def _price_per_million(self, value):
        return self._price_float(value) * 1_000_000

    @api.model
    def get_selection(self):
        return [
            (model.model_id, model.name)
            for model in self.sudo().search([
                ('active', '=', True),
                ('allowed', '=', True),
            ])
        ]

    @api.model
    def action_open_model_management(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Allowed OpenRouter Models'),
            'res_model': self._name,
            'view_mode': 'list,form',
            'domain': [('active', '=', True)],
            'context': {'search_default_active': 1},
        }
