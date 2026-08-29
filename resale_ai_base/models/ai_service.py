import json
import re

from odoo import models


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
