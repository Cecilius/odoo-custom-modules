# Odoo 19 module structure: checkout collection + manual invoice review

## Rule set implemented
- Spain B2C and total `<= 400 EUR`: simplified invoice allowed.
- Spain B2C and total `> 400 EUR`: full invoice and tax ID required.
- Spain B2B: full invoice and tax ID required.
- Foreign B2B: full invoice and tax ID required.
- Foreign B2C: full invoice by default, tax ID not strictly required unless the order is treated as business.

## Workflow in this scaffold
1. Customer places the order on the webshop.
2. Checkout asks for tax ID only when the order logic says it is needed.
3. Sales order stays in `Pending review`.
4. Staff checks customer type, country, amount, and tax ID.
5. Staff approves invoice review.
6. Only after approval can the invoice be posted.
7. Simplified invoices are routed to the simplified journal automatically.

## Main module behavior
- `sale.order` computes whether the sale must use a full invoice and tracks review state.
- `account.move` blocks posting until invoice review is approved and tax ID is present when required.
- `website_sale` can request tax ID during checkout when needed.

## Notes
- This is a strict business policy for operational simplicity.
- You should still test website/controller hooks and inherited form views on your exact Odoo 19 build.
- For robust linkage between invoices and sales orders, replacing the `invoice_origin` lookup with a direct relational approach would be better in production.
