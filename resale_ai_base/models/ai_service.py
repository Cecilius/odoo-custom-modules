import json
import re

from odoo import models
from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.exceptions import UserError


class ResaleAIRequestError(UserError):
    """Provider request failure that is safe for a feature to retry."""


class ResaleAIService(models.AbstractModel):
    """Shared non-provider-specific helpers for resale AI wizards."""

    _name = 'resale.ai.service'
    _description = 'Resale AI Service Helpers'

    def get_agent(self, config_key):
        """Return the configured AI agent, or an empty recordset if unset."""
        value = self.env['ir.config_parameter'].sudo().get_param(config_key)
        return (
            self.env['ai.agent'].browse(int(value)).exists()
            if value and value.isdigit()
            else self.env['ai.agent']
        )

    @staticmethod
    def parse_json_response(response):
        """Normalize provider responses and parse the JSON payload they contain."""
        raw = response[-1] if response else ''
        cleaned = re.sub(
            r'^```(?:json)?|```$', '', raw.strip(), flags=re.MULTILINE,
        ).strip()
        result = json.loads(cleaned)
        if isinstance(result, dict) and result.get('candidates'):
            text = result['candidates'][0]['content']['parts'][0].get('text', '')
            result = json.loads(text)
        return result

    def request_llm(
        self, agent, system_prompts, user_prompts, schema=None,
        service_class=LLMApiService,
    ):
        """Call an agent and mark only provider failures as retryable."""
        provider = agent._get_provider()
        service = service_class(self.env, provider=provider)
        try:
            return service.request_llm(
                agent.llm_model,
                system_prompts,
                user_prompts,
                schema=schema if provider != 'google' else None,
                web_grounding=agent.web_search,
            )
        except UserError as error:
            raise ResaleAIRequestError(str(error)) from error
