import logging
import os

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class GoogleModel(models.Model):
    _name = 'ai.google.model'
    _description = 'Google Gemini Model'
    _order = 'name, model_id'

    model_id = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    description = fields.Text()
    input_token_limit = fields.Integer()
    output_token_limit = fields.Integer()
    supported_generation_methods = fields.Char()
    active = fields.Boolean(default=True)
    allowed = fields.Boolean(
        string='Allowed for AI agents',
        help='Only allowed models are available in the AI agent model selector.',
    )
    last_seen = fields.Datetime()

    _model_id_unique = models.UniqueIndex('(model_id)')

    @api.model
    def _get_api_key(self):
        """Return the configured Gemini key, falling back to the environment."""
        key = self.env['ir.config_parameter'].sudo().get_param('ai.google_key')
        key = key or os.getenv('ODOO_AI_GEMINI_TOKEN')
        if not key:
            raise UserError(_("No API key set for provider 'google'"))
        return key

    @api.model
    def _fetch_models(self):
        """Fetch every Gemini model page exposed by the AI Studio API."""
        key = self._get_api_key()
        models_data = []
        page_token = None
        while True:
            params = {}
            if page_token:
                params['pageToken'] = page_token
            try:
                # Google uses a page token rather than offset-based pagination.
                response = requests.get(
                    'https://generativelanguage.googleapis.com/v1beta/models',
                    params=params,
                    headers={'x-goog-api-key': key},
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.exceptions.RequestException, ValueError) as error:
                _logger.warning('Google Gemini model synchronization failed: %s', error)
                raise UserError(_('Unable to retrieve Google Gemini models: %s', error))
            models_data.extend(payload.get('models') or [])
            page_token = payload.get('nextPageToken')
            if not page_token:
                return models_data

    @api.model
    def _is_supported_model(self, model_data):
        """Return whether a Gemini model supports text generation for agents."""
        return 'generateContent' in (model_data.get('supportedGenerationMethods') or [])

    @api.model
    def action_sync_models(self):
        """Refresh the local Gemini catalog and deactivate missing models.

        Newly discovered models remain disallowed until an administrator
        explicitly approves them for use by AI agents.
        """
        model_data = self._fetch_models()
        supported_models = [model for model in model_data if self._is_supported_model(model)]
        now = fields.Datetime.now()
        catalog = self.sudo()
        seen_ids = set()
        for model in supported_models:
            model_id = (model.get('name') or '').removeprefix('models/')
            if not model_id:
                continue
            seen_ids.add(model_id)
            values = {
                'name': model.get('displayName') or model_id,
                'description': model.get('description'),
                'input_token_limit': model.get('inputTokenLimit') or 0,
                'output_token_limit': model.get('outputTokenLimit') or 0,
                'supported_generation_methods': ','.join(model.get('supportedGenerationMethods') or []),
                'active': True,
                'last_seen': now,
            }
            existing = catalog.search([('model_id', '=', model_id)], limit=1)
            if existing:
                existing.write(values)
            else:
                catalog.create(dict(values, model_id=model_id))

        # An empty upstream response is treated as a failed/incomplete sync.
        # Never deactivate the entire local catalog on that basis.
        if not seen_ids:
            raise UserError(_('Google Gemini returned no compatible models; the existing catalog was left unchanged.'))

        catalog.search([('model_id', 'not in', list(seen_ids))]).write({'active': False})
        _logger.info(
            'Synchronized %s Google Gemini models; %s passed AI guardrails',
            len(model_data), len(seen_ids),
        )
        return len(seen_ids)

    @api.model
    def get_selection(self):
        """Return approved, active Gemini models for a selection field."""
        return [
            (model.model_id, model.name)
            for model in self.sudo().search([('active', '=', True), ('allowed', '=', True)])
        ]

    @api.model
    def action_open_model_management(self):
        """Open the administrator-facing Gemini model catalog."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Allowed Google Gemini Models'),
            'res_model': self._name,
            'view_mode': 'list,form',
            'domain': [('active', '=', True)],
        }
