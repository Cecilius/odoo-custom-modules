from odoo.addons.ai.utils import llm_providers


OPENROUTER_LLMS = [
]

try:
    OPENROUTER_PROVIDER = llm_providers.Provider(
        'openrouter',
        'OpenRouter',
        'openai/text-embedding-3-small',
        {'max_batch_size': 2048, 'max_tokens_per_request': 200000},
        OPENROUTER_LLMS,
        [],
    )
except TypeError:
    try:
        OPENROUTER_PROVIDER = llm_providers.Provider(
            'openrouter',
            'OpenRouter',
            'openai/text-embedding-3-small',
            {'max_batch_size': 2048, 'max_tokens_per_request': 200000},
            OPENROUTER_LLMS,
        )
    except TypeError:
        # Odoo 19 Enterprise revisions before provider batch limits used four fields.
        OPENROUTER_PROVIDER = llm_providers.Provider(
            'openrouter',
            'OpenRouter',
            'openai/text-embedding-3-small',
            OPENROUTER_LLMS,
        )

if not any(provider.name == OPENROUTER_PROVIDER.name for provider in llm_providers.PROVIDERS):
    llm_providers.PROVIDERS.append(OPENROUTER_PROVIDER)
    llm_providers.EMBEDDING_MODELS_SELECTION.append(
        (OPENROUTER_PROVIDER.embedding_model, OPENROUTER_PROVIDER.display_name)
    )
