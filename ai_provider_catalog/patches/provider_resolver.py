from odoo.addons.ai.models import ai_agent
from odoo.addons.ai.utils import llm_providers
from odoo.exceptions import UserError
from odoo import _


_original_get_provider = llm_providers.get_provider


def _find_catalog_model(env, llm_model):
    """Return the provider for an active catalog entry, if any."""
    for model_name, provider_name in (
        ('ai.openrouter.model', 'openrouter'),
        ('ai.google.model', 'google'),
    ):
        if model_name not in env:
            continue
        record = env[model_name].sudo().search([
            ('model_id', '=', llm_model),
        ], limit=1)
        if record:
            if record.active:
                return provider_name
            raise UserError(_("The selected AI model is no longer available."))
    return None


def _get_provider(env, llm_model):
    provider = _find_catalog_model(env, llm_model)
    if provider:
        return provider
    return _original_get_provider(env, llm_model)


llm_providers.get_provider = _get_provider
ai_agent.get_provider = _get_provider
