"""Extension hooks for provider-specific AI service behavior."""

LLM_REQUEST_HANDLERS = {}


def register_llm_request_handler(provider, handler):
    """Register the single-request handler for an AI provider."""
    LLM_REQUEST_HANDLERS[provider] = handler


def get_llm_request_handler(provider):
    """Return the registered single-request handler for ``provider``."""
    return LLM_REQUEST_HANDLERS.get(provider)
