# AI OpenRouter Provider

Adds OpenRouter support to the Odoo 19 Enterprise `ai` module.

Initial test models:

- `nvidia/nemotron-3.5-lightning:free`
- `liquid/lfm-2.5-2.6b:free`

The Odoo server sends requests to `https://openrouter.ai/api/v1`. Configure the
API key in the AI integration settings. The optional `ODOO_AI_OPENROUTER_TOKEN`
environment variable can be used for deployments that do not store the key in
the database.

The adapter currently supports text chat, tool calls, structured outputs,
images, and OpenRouter embeddings. OpenRouter web grounding and arbitrary PDF
uploads are intentionally not enabled yet.
