# Spain Simplified Invoice Workflow

This module reuses the Spanish localization simplified invoice logic and adds review controls around invoice posting.

## Features
- Automatic journal assignment from company settings.
- Invoice review state on sales orders.
- Wizard-based confirmation for journal mismatches and over-limit Spanish invoices without VAT/NIF.
- Checkout VAT handling aligned with the same company limit.

## Posting rules
- Simplified invoice + simplified journal: post normally.
- Full invoice + full journal: post normally.
- Journal mismatch: open the confirmation wizard.
- Over-limit Spanish invoice without VAT/NIF: open the confirmation wizard.

## Tests
- One test covers the over-limit confirmation path.
- One test covers the journal mismatch confirmation path.

## Notes
Comments are intentionally sparse and only explain the non-obvious business-rule branches.
