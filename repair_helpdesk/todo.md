# Repair Helpdesk Module TODO

## Sprint 1 — Core workflow stabilization
- [x] Update `__manifest__.py` to add `stock` and optionally `delivery` to `depends`
- [x] Add inbound/outbound shipment tracking fields to `helpdesk.ticket`
- [x] Add carrier, tracking number, and shipment status information to tickets
- [x] Confirm sales order stage automation for quotation sending and confirmation
- [x] Prepare repair order workflow sync hooks from `repair.order` to helpdesk ticket

## Sprint 2 — Logistics integration
- [ ] Create incoming shipment from a helpdesk ticket
- [ ] Confirm device receipt and move ticket to `Awaiting item`
- [ ] Create return shipment from a ticket when repair is complete
- [ ] Automate stage transitions based on picking events (inbound/outbound)
- [ ] Visualize connection between helpdesk ticket and a shipment (shipment scree -> Additional Info, just below Sales Order)

## Sprint 3 — Repair lifecycle automation
- [ ] Sync repair order state changes to helpdesk ticket stages
- [ ] Map repair diagnostics to `Diagnostics in progress`
- [ ] Map active repair work to `Under repair`
- [ ] Map part waiting state to `Waiting for parts`
- [ ] Map repair completion to `Quality control` or `Ready for shipment`
- [ ] Add technician assignment fields and make them visible on the ticket

## Sprint 4 — Quote and service option refinements
- [ ] Support revised quotations and stage move to revised approval
- [ ] Ensure ticket stage changes only after quotation is actually sent/confirmed
- [ ] Add pickup vs courier return options in quotes
- [ ] Make return shipping optional or auto-remove it for pickup
- [ ] Add optional insured or expedited shipping service lines

## Sprint 5 — Payment and closure automation
- [ ] Link helpdesk tickets to invoices and payment records
- [ ] Add invoice/payment status helper fields to tickets
- [ ] Move ticket stage after invoice validation/payment receipt
- [ ] Close tickets only after return shipment delivery or customer pickup

## Sprint 6 — Technician UI and workspace
- [ ] Add repair-focused kanban/dashboard views for the repair team
- [ ] Add quick actions for receive device, start diagnostics, and ship return
- [ ] Add smart buttons for related sales orders, repair orders, shipments, and invoices
- [ ] Make Helpdesk the main technician workspace with a cleaner workflow view
