import json
import os

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.ai.utils.llm_api_service import LLMApiService


_original_init = LLMApiService.__init__
_original_get_api_token = LLMApiService._get_api_token
_original_request_llm = LLMApiService._request_llm
_original_build_tool_call_response = LLMApiService._build_tool_call_response


def _init(self, env, provider='openai'):
    if provider != 'openrouter':
        return _original_init(self, env, provider)
    self.provider = provider
    self.base_url = 'https://openrouter.ai/api/v1'
    self.env = env


def _get_api_token(self):
    if self.provider != 'openrouter':
        return _original_get_api_token(self)
    key = self.env['ir.config_parameter'].sudo().get_param('ai.openrouter_key')
    key = key or os.getenv('ODOO_AI_OPENROUTER_TOKEN')
    if not key:
        raise UserError(_("No API key set for provider '%s'", self.provider))
    return key


def _get_openrouter_headers(self):
    headers = self._get_base_headers()
    params = self.env['ir.config_parameter'].sudo()
    if referer := params.get_param('ai.openrouter_http_referer'):
        headers['HTTP-Referer'] = referer
    if title := params.get_param('ai.openrouter_title'):
        headers['X-OpenRouter-Title'] = title
    return headers


def _request_llm_openrouter(
    self, llm_model, system_prompts, user_prompts, tools=None,
    files=None, schema=None, temperature=0.2, inputs=(), web_grounding=False,
):
    messages = [{'role': 'system', 'content': prompt} for prompt in system_prompts]
    if user_prompts:
        messages.append({'role': 'user', 'content': '\n\n'.join(user_prompts)})
    messages.extend(inputs or ())

    if files:
        content = []
        for file in files:
            if file['mimetype'] == 'text/plain':
                content.append({'type': 'text', 'text': file['value']})
            elif file['mimetype'].startswith('image/'):
                content.append({
                    'type': 'image_url',
                    'image_url': {'url': f"data:{file['mimetype']};base64,{file['value']}"},
                })
            else:
                raise NotImplementedError(
                    _('OpenRouter does not support this file type in the current adapter: %s', file['mimetype'])
                )
        messages.append({'role': 'user', 'content': content})

    body = {
        'model': llm_model,
        'messages': messages,
        'temperature': temperature,
    }
    if schema:
        body['response_format'] = {
            'type': 'json_schema',
            'json_schema': {'name': 'odoo_response', 'strict': True, 'schema': schema},
        }
    if tools:
        body['tools'] = [{
            'type': 'function',
            'function': {
                'name': tool_name,
                'description': tool_description,
                'parameters': tool_parameter_schema,
            },
        } for tool_name, (tool_description, __, __, tool_parameter_schema) in tools.items()]
        body['tool_choice'] = 'auto'
    if web_grounding and not any(
        message.get('role') == 'tool' or message.get('tool_calls')
        for message in (inputs or ())
    ):
        body['plugins'] = [{
            'id': 'web',
            'max_results': min(max(int(self.env.context.get('ai_web_search_max_results', 3)), 1), 5),
        }]

    response = self._request(
        method='post',
        endpoint='/chat/completions',
        headers=_get_openrouter_headers(self),
        body=body,
    )
    choice = (response.get('choices') or [{}])[0]
    message = choice.get('message') or {}
    next_inputs = list(inputs or ())
    tool_calls = message.get('tool_calls') or []

    if tool_calls:
        next_inputs.append({
            'role': 'assistant',
            'content': message.get('content'),
            'tool_calls': tool_calls,
        })
        parsed_calls = []
        for tool_call in tool_calls:
            function = tool_call.get('function') or {}
            try:
                arguments = json.loads(function.get('arguments') or '{}')
            except json.JSONDecodeError:
                continue
            parsed_calls.append((function.get('name'), tool_call.get('id'), arguments))
        return [], parsed_calls, next_inputs

    content = message.get('content')
    return ([content] if content else []), [], next_inputs


def _request_llm(self, *args, **kwargs):
    if self.provider == 'openrouter':
        return _request_llm_openrouter(self, *args, **kwargs)
    return _original_request_llm(self, *args, **kwargs)


def _build_tool_call_response(self, tool_call_id, return_value):
    if self.provider == 'openrouter':
        return {
            'role': 'tool',
            'tool_call_id': tool_call_id,
            'content': str(return_value),
        }
    return _original_build_tool_call_response(self, tool_call_id, return_value)


LLMApiService.__init__ = _init
LLMApiService._get_api_token = _get_api_token
LLMApiService._request_llm = _request_llm
LLMApiService._build_tool_call_response = _build_tool_call_response
