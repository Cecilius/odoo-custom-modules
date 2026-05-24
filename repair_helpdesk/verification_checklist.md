# Verification Checklist — Repair Helpdesk Logistics

This standalone checklist is separate from the general TODO list and focused on verifying the implemented logistics flows.

## Pre-requisites
- Odoo server running with the `repair_helpdesk` module installed and updated.
- Current branch includes the latest model/view changes.
- A user with access to Helpdesk, Stock, Sales, and Repair apps.

## Shipments
- [ ] Create a helpdesk ticket with a customer and (optional) product details.
- [ ] From the ticket, click "Create incoming shipment": verify the incoming `stock.picking` opens directly in **form** view.
- [ ] On the created incoming picking: confirm `helpdesk_ticket_id` is set and the `origin` contains the ticket reference.
- [ ] Use `View Shipments` on the ticket when only one picking exists: confirm it opens the picking `form` view.
- [ ] Create a second incoming picking for the same ticket (or a second related shipment) and use `View Shipments`: confirm a **list** (tree) view appears and the domain filters to the ticket's shipments.
- [ ] From a validated incoming picking, create an outgoing shipment via the ticket: verify outgoing `stock.picking` opens directly in **form** view, contains `move_lines`/`move_ids` with expected products and quantities, and is linked to the ticket.
- [ ] Attempt to create an outgoing shipment when no validated incoming exists: verify the system raises the expected error message.

## Quotations
- [ ] From the ticket, create a quotation: verify the created `sale.order` opens directly in **form** view and is in `draft` state.
- [ ] Confirm the ticket does NOT move to quotation approval automatically when the quotation is created.
- [ ] Send/Confirm the quotation and verify the ticket stage changes as coded (test `send` and `confirm` behaviors).

## Repair Orders
- [ ] Create a repair order from the ticket: verify the `repair.order` opens directly in **form** view.
- [ ] Confirm the ticket moves to the `Initial Inspection` stage after creating the repair order.

## Inventory Locations & Flow (repair-only locations)
- [ ] Confirm the following dedicated locations exist, or create them if missing:
  - `Incoming Inspection Location`
  - `Awaiting Repair Location`
  - `Repair In Progress Location`
  - `Quality Control / Awaiting Shipment`
  - `Repair Return Dispatch`
- [ ] Receive a device into `Incoming Inspection Location` and confirm stock quants are created there (product, lot if applicable).
- [ ] Move device to `Awaiting Repair Location` after inspection and confirm move is recorded and quantities updated.
- [ ] Move device to `Repair In Progress Location` when work starts, and to `Quality Control / Awaiting Shipment` when repair completes.
- [ ] Create outgoing picking that uses `Repair Return Dispatch` as source or staging location before transfer to customer.

## Edge Cases & UX
- [ ] Verify `action_view_shipments` behavior when `picking_count == 0` — ensure it opens a filtered empty list rather than failing or opening an empty form.
- [ ] Verify direct-open returns (incoming/outgoing/quotation/repair) work in multi-user sessions and do not open blank new records.
- [ ] Verify `move_ids` construction for outgoing shipments contains correct descriptions and uses `description_picking` where needed.

## Post-check & CI
- [ ] Run a syntax check for Python files modified in the module:

```bash
python3 -m py_compile odoo-custom-modules/repair_helpdesk/models/helpdesk_ticket.py
```

- [ ] Run module update and restart Odoo (example):

```bash
# from the Odoo project root
./odoo-bin -c ./odoo-enterprise/debian/odoo.conf -d your_db -u repair_helpdesk
```

- [ ] Commit and push any follow-up fixes:

```bash
git add odoo-custom-modules/repair_helpdesk/models/helpdesk_ticket.py
git commit -m "Fix: ..."
git push origin 19.0-develop
```

## Notes
- If you want, I can convert the location draft into Odoo `stock.location` creation XML (data file) and add a migration script to create these locations automatically.
