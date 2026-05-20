# Odoo 19 module structure: reuse Spanish localization simplified invoice logic

## Purpose
This module reuses the Spanish localization fields `l10n_es_is_simplified` and `l10n_es_simplified_invoice_limit`, and adds workflow controls around them.

## What this module adds
- Manual invoice review state on `sale.order`.
- Company settings for a simplified sales journal and a full sales journal.
- Automatic journal assignment based on `l10n_es_is_simplified`.
- Soft blocking on journal mismatch or missing VAT for non-simplified Spanish invoices.

## Notes on comments
Comments are only used where the code is intentionally non-obvious:
- to explain why localization logic is reused rather than duplicated,
- to explain why mismatch checks soft-block instead of only logging,
- to mark this as a warning-first implementation that may be tightened later.

## External references
- Stack Overflow comment guidance: https://stackoverflow.blog/2021/12/23/best-practices-for-writing-code-comments/
- Odoo Spain localization docs: https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations/spain.html
