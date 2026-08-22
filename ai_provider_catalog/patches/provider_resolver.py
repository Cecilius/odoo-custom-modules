from odoo.addons.ai.models import ai_agent
from odoo.addons.ai.utils import llm_providers
from odoo.exceptions import UserError


_original_get_provider = llm_providers.get_provider


def _get_provider(env, llm_model):
    try:
        provider = _original_get_provider(env, llm_model)
    except UserError:
        provider = None

    if provider == 'google' and 'ai.google.model' in env and env['ai.google.model'].sudo().search_count([
        ('model_id', '=', llm_model),
    ]):
        if env['ai.google.model'].sudo().search_count([
            ('model_id', '=', llm_model), ('active', '=', True),
        ]):
            return 'google'
        raise UserError('The selected Google Gemini model is no longer available.')

    if provider:
        return provider

    for model_name, provider_name in (
        ('ai.openrouter.model', 'openrouter'),
        ('ai.google.model', 'google'),
    ):
        if model_name in env and env[model_name].sudo().search_count([
            ('model_id', '=', llm_model),
            ('active', '=', True),
        ]):
            return provider_name
    return _original_get_provider(env, llm_model)


llm_providers.get_provider = _get_provider
ai_agent.get_provider = _get_provider
