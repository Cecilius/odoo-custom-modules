# Repair Helpdesk — Process Flow and Module Interaction

This document describes the repair intake, inspection, repair, and return flow and which Odoo modules are responsible for each step.

## High-level flow

```mermaid
flowchart TD
  Helpdesk[Helpdesk Ticket]
  Stock[Stock / Picking]
  Quality[Quality]
  Repair[Repair (repair.order)]
  Sales[Sales / Quotation]
  Locations[Repair Locations]

  Helpdesk -->|Create incoming picking| Stock
  Stock -->|Validate incoming picking| Quality
  Quality -->|Inspection pass| Stock
  Quality -->|Inspection fail| Helpdesk
  Stock -->|Move to repair location| Repair
  Repair -->|Work done| Quality
  Repair -->|Request return shipment| Stock
  Sales -->|Quotation created from ticket| Helpdesk

  subgraph Inventory
    Locations
  end

  Locations --- Stock
  Locations --- Repair
```
```

## Sequence of events (detailed)

1. Create Helpdesk ticket (module: `helpdesk`). Ticket holds customer, device, reported issue.
2. From ticket: create an Incoming Picking (module: `stock`). Picking uses `Incoming Inspection Location` as destination.
3. On Picking validation: automatically create or link a `quality.inspection` (module: `quality`).
   - If inspection is required, a `quality.checkpoint` is used (e.g. "Incoming Inspection (Repairs)").
4. Inspection outcome (module: `quality`):
   - Pass: move stock from `Incoming Inspection Location` to `Awaiting Repair Location` and update `helpdesk.ticket` stage to `Awaiting item` (or equivalent).
   - Fail: mark ticket and picking appropriately, optionally trigger return or customer notification.
5. Technician creates/links a `repair.order` (module: `repair`) and performs repair actions; stock moves to `Repair In Progress Location` while work occurs.
6. After repair and QC: move to `Quality Control / Awaiting Shipment` location; create Outgoing Picking for return (module: `stock`).
7. Create `sale.order` quotation from the ticket if repair services are billable (module: `sale`). Quotation send/confirm events may move ticket stages.

## Responsibilities by module

- `repair_helpdesk` (custom module)
  - Orchestrates creation of pickings, sale orders, and repair orders from the ticket UI.
  - Stores links (`helpdesk_ticket_id`) on `stock.picking`, `sale.order`, `repair.order`.
  - Provides smart buttons and quick-actions.

- `stock` / `stock_picking`
  - Handles physical receipt and dispatch of devices.
  - Interacts with repair locations and pickings.

- `quality`
  - Manages inspection checkpoints and inspections for incoming goods.
  - Triggers rules based on inspection results (pass/fail) to move goods or update tickets.

- `repair`
  - Tracks repair work, parts consumption, and links to device lots when applicable.

- `sale`
  - Creates quotations for diagnostic/repair services and handles billing confirmation.

## Suggested configuration items to implement

- Add `quality` to `depends` in `__manifest__.py` of `repair_helpdesk`.
- Add `data/repair_locations.xml` to create the five repair-specific `stock.location` records.
- Add `data/quality_checkpoint.xml` to create a `quality.checkpoint` named "Incoming Inspection (Repairs)" and attach it to incoming pickings/picking types.
- Add an automated hook in `stock.picking` (on `button_validate`) to create or link a `quality.inspection` for the picking when it arrives from a helpdesk ticket.
- Add server action or automated rule to handle inspection results and move stock + update ticket stage accordingly.

## Next actionable options (I can do any of these)
- Implement the `data/*.xml` files to create locations and checkpoint records.
- Add the `quality` dependency to `__manifest__.py` and a small hook to create inspections automatically.
- Implement the inspection result handlers and tests.


