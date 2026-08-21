from odoo.addons.ai.models import ai_agent
from odoo.addons.ai.utils.llm_api_service import LLMApiService


_original_agent_generate_response = ai_agent.AIAgent._generate_response
_original_request_llm = LLMApiService.request_llm


def _generate_response(self, *args, **kwargs):
    if self.web_search:
        self = self.with_context(
            ai_web_search=True,
            ai_web_search_max_results=self.web_search_max_results,
        )
    return _original_agent_generate_response(self, *args, **kwargs)


def _request_llm(self, *args, **kwargs):
    if self.provider in ('openrouter', 'google') and self.env.context.get('ai_web_search'):
        kwargs['web_grounding'] = True
    return _original_request_llm(self, *args, **kwargs)


ai_agent.AIAgent._generate_response = _generate_response
LLMApiService.request_llm = _request_llm
