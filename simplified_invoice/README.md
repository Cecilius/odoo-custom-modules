# Odoo 19 module structure: reuse Spanish localization simplified invoice logic

## Purpose
This module no longer reimplements the Spanish simplified invoice threshold logic. Instead, it reuses the existing Spanish localization field `l10n_es_is_simplified` and the existing company setting `l10n_es_simplified_invoice_limit`.

## What this module adds
- Manual invoice review state on `sale.order`.
- Blocking invoice posting until review is approved.
- Reuse of `l10n_es_is_simplified` to decide whether simplified journal routing should happen.
- Exposure of the Spain localization settings block when the company country is Spain.
- Checkout VAT requirement aligned with the localization limit for Spanish orders.

## Core behavior
- If Spanish localization marks the invoice as simplified, the module can route it to the simplified sales journal.
- If the invoice is not simplified and the Spanish workflow requires tax ID, posting is blocked when VAT/NIF is missing.
- The company setting `l10n_es_simplified_invoice_limit` is reused instead of a duplicate custom threshold.

## Notes
- This keeps the business workflow customization smaller and more compatible with Odoo 19 Spain localization.
- The module still adds manual review before posting/shipping, which is outside the base localization logic.
- Production use should still include tests on your exact enterprise build.
