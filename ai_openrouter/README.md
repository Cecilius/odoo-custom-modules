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
