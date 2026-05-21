# Spain Simplified Invoice Workflow

This module reuses the Spanish localization simplified invoice logic and adds review and validation controls around invoice posting, with a focus on future VeriFactu-style real‑time reporting.

## Features

- Automatic journal assignment from company settings (simplified vs full sales journals).
- Invoice review state on sales orders.
- Hard validations for:
  - over‑limit invoices incorrectly marked as simplified,
  - over‑limit Spanish invoices without VAT/NIF,
  - any simplified invoice issued to a customer outside Spain.
- Wizard-based confirmation when the simplified flag and the selected journal do not match.
- Checkout VAT handling aligned with the company’s Spanish simplified invoice limit.

## Posting rules

- Simplified invoice + simplified journal, within the simplified limit, Spanish customer with valid data: posts normally.
- Full invoice + full journal: posts normally when VAT/NIF is present where required.
- Over-limit invoice marked as simplified: blocked with an error.
- Over-limit Spanish invoice without VAT/NIF: blocked with an error.
- Simplified invoice for a non-Spanish customer: blocked with an error.
- Full invoice for a Spanish customer (simplified flag is False) without VAT/NIF: blocked with an error.
- Journal mismatch between simplified flag and journal: opens the confirmation wizard, allowing the user to switch to simplified/full before posting.

## Tests

The automated tests cover:

- Over‑limit simplified invoices raising an error.
- Over‑limit Spanish invoices without VAT/NIF raising an error.
- Blocking simplified invoices for non‑Spanish customers.
- Blocking full invoices for Spanish customers without VAT/NIF.
- Ensuring the Spanish VAT rule does not block non‑Spanish customers.
- Opening the confirmation wizard when the journal and simplified flag disagree.

## Notes

Comments are intentionally minimal and only explain non‑obvious branches, such as why certain validations are hard errors instead of wizard prompts, and how they relate to Spanish simplified invoice rules and future VeriFactu compliance.