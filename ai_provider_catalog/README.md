# AI Provider Catalog

Shared runtime support for dynamically synchronized and administrator-approved
AI provider models. Existing agents retain their configured model during
migration when that model becomes inactive or disallowed.

## Implementation note: import-time patches

Odoo 19's `LLMApiService` has no extension hook for additional providers, so
this module patches it when its Python package is imported. Python code is
loaded per server process, which means the patch is active for **every
database served by that process**, even databases where the module is not
installed. This is harmless with one database per instance (as on the
production and staging servers), but keep it in mind on multi-database
servers: install the module consistently or run it on a dedicated instance.
