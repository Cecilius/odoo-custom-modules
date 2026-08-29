"""Compatibility bridge for Odoo's non-extensible LLMApiService dispatcher."""

from odoo.addons.ai.utils.llm_api_service import LLMApiService

from ..hooks import get_llm_request_handler


_original_request_llm = getattr(
    LLMApiService._request_llm,
    '_ai_provider_catalog_original',
    LLMApiService._request_llm,
)


def _request_llm(self, *args, **kwargs):
    """Dispatch through a registered adapter while preserving Odoo defaults."""
    if self.provider in ('google', 'openrouter') and self.env.context.get('ai_web_search'):
        kwargs['web_grounding'] = True
    handler = get_llm_request_handler(self.provider)
    if handler:
        return handler(self, *args, **kwargs)
    return _original_request_llm(self, *args, **kwargs)


_request_llm._ai_provider_catalog_original = _original_request_llm
LLMApiService._request_llm = _request_llm
