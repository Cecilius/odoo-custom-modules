from odoo.addons.ai.utils.llm_api_service import LLMApiService

_original_request = LLMApiService._request


def _request(self, *args, **kwargs):
    if 'timeout' not in kwargs:
        try:
            timeout = int(
                self.env['ir.config_parameter'].sudo().get_param('ai.request_timeout', '120')
            )
        except (TypeError, ValueError):
            timeout = 120
        kwargs['timeout'] = max(timeout, 1)
    return _original_request(self, *args, **kwargs)


LLMApiService._request = _request
