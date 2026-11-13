# AI OpenRouter Provider

Adds OpenRouter support to the Odoo 19 Enterprise `ai` module. Shared model
approval and agent behavior are provided by `ai_provider_catalog`.

Initial test models:

- `nvidia/nemotron-3.5-lightning:free`
- `liquid/lfm-2.5-2.6b:free`

The Odoo server sends requests to `https://openrouter.ai/api/v1`. Configure the
API key in the AI integration settings. The optional `ODOO_AI_OPENROUTER_TOKEN`
environment variable can be used for deployments that do not store the key in
the database.

The adapter supports text chat, tool calls, structured outputs, images,
OpenRouter embeddings, and bounded web search. Arbitrary PDF uploads are not
enabled yet.

After installing the module, synchronize the provider catalog from the AI
integration settings and explicitly approve the models that agents may use.
Models omitted by OpenRouter are deactivated, while existing agents retain
their current model selection so administrators can migrate them safely.

## Implementation note: import-time patches

Odoo 19's `LLMApiService` has no extension hook for additional providers, so
this module patches it when its Python package is imported. Python code is
loaded per server process, which means the patch is active for **every
database served by that process**, even databases where the module is not
installed. This is harmless with one database per instance (as on the
production and staging servers), but keep it in mind on multi-database
servers: install the module consistently or run it on a dedicated instance.
