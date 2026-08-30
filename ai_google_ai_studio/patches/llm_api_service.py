"""Gemini v1 interactions API adapter for Odoo's LLMApiService.

The new ``v1/interactions`` endpoint is session/step oriented and uses
snake_case JSON fields. This module registers a request handler for the
``google`` provider that translates Odoo's tool/chat contract to the
interactions API while preserving the legacy ``generateContent`` path for
models explicitly configured with ``api_mode = generate_content``.
"""

import logging

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.ai.utils.ai_logging import api_call_logging
from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.addons.ai.utils.llm_providers import get_llm_model_and_reasoning
from odoo.addons.ai_provider_catalog.hooks import register_llm_request_handler


_logger = logging.getLogger(__name__)

INTERACTIONS_BASE_URL = 'https://generativelanguage.googleapis.com/v1'
# Internal marker carried in ``inputs`` between tool-call rounds so the next
# request can link to the previous interaction via ``previous_interaction_id``.
INTERACTION_ID_MARKER = '__google_interaction_id'


_request_llm_google_orig = LLMApiService._request_llm_google


def _extract_input_steps(inputs):
    """Split Odoo/generateContent-style inputs into interactions steps.

    :param inputs: list of ``{"role": ..., "parts": [...]}`` messages.
    :return: ``(steps, previous_interaction_id)`` where ``steps`` are
        snake_case interactions steps and ``previous_interaction_id`` is the
        marker-carried id of the previous interaction, if any.
    """
    steps = []
    previous_interaction_id = None
    for item in inputs or ():
        if not isinstance(item, dict):
            continue
        if interaction_id := item.get(INTERACTION_ID_MARKER):
            previous_interaction_id = interaction_id
            continue
        role = item.get('role')
        for part in item.get('parts') or ():
            if not isinstance(part, dict):
                continue
            if text := part.get('text'):
                steps.append({
                    'type': 'user_input' if role == 'user' else 'model_output',
                    'content': [{'type': 'text', 'text': text}],
                })
            elif 'functionCall' in part:
                call = part['functionCall']
                steps.append({
                    'type': 'function_call',
                    'id': call.get('id') or call.get('name') or '',
                    'name': call.get('name') or '',
                    'arguments': call.get('args') or {},
                })
            elif 'functionResponse' in part:
                fr = part['functionResponse']
                steps.append({
                    'type': 'function_result',
                    'call_id': fr.get('id') or fr.get('name') or '',
                    'name': fr.get('name') or '',
                    'result': str((fr.get('response') or {}).get('result', '')),
                })
    return steps, previous_interaction_id


def _build_file_content(file):
    """Map an Odoo file dict to an interactions content block."""
    mimetype = file.get('mimetype') or ''
    if mimetype == 'text/plain':
        return {'type': 'text', 'text': file.get('value', '')}
    if mimetype.startswith('image/'):
        return {'type': 'image', 'data': file.get('value', ''), 'mime_type': mimetype}
    if mimetype == 'application/pdf':
        return {'type': 'document', 'data': file.get('value', ''), 'mime_type': mimetype}
    raise NotImplementedError(_('Gemini interactions does not support this file type: %s', mimetype))


def _build_interaction_input(user_prompts, files, prior_steps):
    """Build the interactions ``input`` field for the first request of a run."""
    current_text = '\n\n'.join(user_prompts)
    if not files:
        if not prior_steps:
            return current_text
        steps = list(prior_steps)
        if current_text:
            steps.append({'type': 'user_input', 'content': [{'type': 'text', 'text': current_text}]})
        return steps
    content = []
    if current_text:
        content.append({'type': 'text', 'text': current_text})
    content.extend(_build_file_content(file) for file in files)
    steps = list(prior_steps)
    steps.append({'type': 'user_input', 'content': content})
    return steps


def _parse_interaction_response(payload):
    """Extract ``(responses, to_call)`` from an interactions payload."""
    to_call = []
    responses = []
    for step in payload.get('steps') or ():
        step_type = step.get('type')
        if step_type == 'function_call':
            to_call.append((
                step.get('name') or '',
                step.get('id') or step.get('name') or '',
                step.get('arguments') or {},
            ))
        elif step_type == 'model_output':
            for content in step.get('content') or ():
                if content.get('type') == 'text' and content.get('text'):
                    responses.append(content['text'])
    return responses, to_call


def _parse_interaction_usage(payload):
    """Map interactions ``usage`` to Odoo's request token usage keys."""
    usage = payload.get('usage') or {}
    if not usage:
        return {}
    return {
        'input_tokens': usage.get('total_input_tokens', 0),
        'cached_tokens': usage.get('total_cached_tokens', 0),
        'output_tokens': usage.get('total_output_tokens', 0),
    }


def _request_llm_google_interactions_helper(
    self, llm_model, system_prompts, user_prompts, tools=None,
    files=None, schema=None, reasoning=None, inputs=(), web_grounding=False,
):
    """Issue a single interactions request and parse its payload."""
    steps, previous_interaction_id = _extract_input_steps(inputs)

    body = {'model': llm_model}
    if system_prompts:
        body['system_instruction'] = '\n\n'.join(system_prompts)

    declared_tools = []
    if tools:
        declared_tools.extend({
            'type': 'function',
            'name': tool_name,
            'description': tool_description,
            'parameters': tool_parameter_schema,
        } for tool_name, (tool_description, __, __, tool_parameter_schema) in tools.items())
    if web_grounding:
        declared_tools.append({'type': 'google_search', 'search_types': ['web_search']})
    if declared_tools:
        body['tools'] = declared_tools

    generation_config = {}
    if reasoning:
        generation_config['thinking_level'] = reasoning
    if generation_config:
        body['generation_config'] = generation_config

    if schema:
        body['response_format'] = {
            'type': 'text',
            'mime_type': 'application/json',
            'schema': schema,
        }

    if previous_interaction_id:
        body['previous_interaction_id'] = previous_interaction_id
        body['input'] = [step for step in steps if step['type'] == 'function_result']
    else:
        body['input'] = _build_interaction_input(user_prompts, files, steps)

    payload = self._request(
        method='post',
        base_url=INTERACTIONS_BASE_URL,
        endpoint='/interactions',
        headers={'x-goog-api-key': self._get_api_token()},
        body=body,
    )

    status = payload.get('status')
    if status in ('failed', 'cancelled', 'budget_exceeded', 'incomplete'):
        errors = payload.get('errors') or []
        message = '; '.join(str(error.get('message') or error) for error in errors)
        if not message:
            message = _('Gemini interaction ended with status %s.', status)
        raise UserError(message)
    if status not in ('completed', 'requires_action', 'in_progress', 'queued'):
        _logger.warning('Gemini interaction returned unexpected status %r', status)

    responses, to_call = _parse_interaction_response(payload)
    next_inputs = list(inputs or ())
    if interaction_id := payload.get('id'):
        next_inputs.append({INTERACTION_ID_MARKER: interaction_id})
    return responses, to_call, next_inputs, _parse_interaction_usage(payload)


def _request_llm_google_interactions(
    self, llm_model, system_prompts, user_prompts, tools=None,
    files=None, schema=None, temperature=0.5, inputs=(), web_grounding=False,
):
    """Translate Odoo's tool/chat contract to the Gemini v1 interactions API."""
    if 'ai.google.model' in self.env:
        model_record = self.env['ai.google.model'].with_context(
            active_test=False,
        ).sudo().search([('model_id', '=', llm_model)], limit=1)
    else:
        model_record = None
    if not model_record or model_record.api_mode == 'generate_content':
        return _request_llm_google_orig(
            self, llm_model, system_prompts, user_prompts, tools=tools, files=files,
            schema=schema, temperature=temperature, inputs=inputs, web_grounding=web_grounding,
        )

    llm_model, reasoning = get_llm_model_and_reasoning(llm_model, temperature)

    with api_call_logging(list(inputs or ()), tools) as record_response:
        response = []
        to_call = []
        next_inputs = list(inputs or ())
        request_token_usage = {}
        for attempt in range(3):
            response, to_call, next_inputs, request_token_usage = (
                _request_llm_google_interactions_helper(
                    self, llm_model, system_prompts, user_prompts, tools=tools, files=files,
                    schema=schema, reasoning=reasoning, inputs=inputs,
                    web_grounding=web_grounding,
                )
            )
            if response or to_call:
                break
            _logger.warning('Gemini interactions failed to generate a response, retrying...')
        if not (response or to_call):
            response = ['Error: failed to generate a response, try again later.']
        if record_response:
            record_response(to_call, response, request_token_usage)
        return response, to_call, next_inputs


register_llm_request_handler('google', _request_llm_google_interactions)