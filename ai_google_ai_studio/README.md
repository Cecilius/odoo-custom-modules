# AI Google AI Studio Provider

Adds synchronized, administrator-approved Google Gemini AI Studio models to
the Odoo 19 Enterprise AI application. Google model metadata does not include
pricing, so this provider does not display estimated costs. Existing agents
retain their current model selection if a model is later disallowed or no
longer returned by Google.

## Implementation note: import-time patches

Odoo 19's `LLMApiService` has no extension hook for additional providers, so
this module patches it when its Python package is imported. Python code is
loaded per server process, which means the patch is active for **every
database served by that process**, even databases where the module is not
installed. This is harmless with one database per instance (as on the
production and staging servers), but keep it in mind on multi-database
servers: install the module consistently or run it on a dedicated instance.
