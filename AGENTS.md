# AGENTS.md

Repo of 3 Odoo 19.0 LGPL-3 custom modules. No build, lint, CI, or test tooling at root.

## Modules

| Module | Purpose | Tests? |
|---|---|---|
| `repair_helpdesk/` | Electronics repair workflow in Helpdesk (most active) | No |
| `simplified_invoice/` | Spanish simplified invoice validation | Yes (7 tests) |
| `pos_custom_receipt_es/` | Custom POS receipt layout (QWeb) | No |

## How to test

- **Module update**: `./odoo-bin -c odoo.conf -d <db> -u <module>` (run from sibling odoo-enterprise dir)
- **Python syntax check**: `python3 -m py_compile <file.py>`
- **Automated tests** (simplified_invoice only): `./odoo-bin -c odoo.conf -d <db> --test-enable -u simplified_invoice`
- **Verification script**: `python3 repair_helpdesk/verify_repair_helpdesk.py -d <db> -c <config>` (requires Odoo env on PYTHONPATH)

## Data loading gotchas

- `repair_helpdesk/data/helpdesk_stage_data.xml` uses `<odoo noupdate="1">` — stages are loaded once and **never re-updated on module upgrade**. Same for `repair_locations.xml`, `helpdesk_team_data.xml`, `product_data.xml`, `incoming_inspection_data.xml` (all use `noupdate="1"`).
- Data file order in `__manifest__.py` `data` list determines load order. Reference data (locations, products) must come before data that depends on them.

## Coding conventions

- **Custom fields**: Use `x_` prefix (e.g. `x_device_description`, `x_serial_number`).
- **View inheritance**: Always `inherit_id` + `xpath`. Valid `position` values: `after`, `before`, `inside`, `replace`, `attributes`.
- **Cross-module link**: `helpdesk_ticket_id` Many2one (with `copy=False, index=True`) is added to `stock.picking`, `sale.order`, `repair.order`.
- **String quotes**: Both single and double quotes are used — don't enforce one.
- **Action methods**: Start with `self.ensure_one()` guard.

## repair_helpdesk architecture

The module orchestrates 7 Odoo modules: `helpdesk`, `sale_management`, `product`, `repair`, `stock`, `delivery`, `quality`.

### Incoming inspection (current design)

The inspection system was simplified from a dual-system approach (Odoo native `quality.point`/`quality.check` + custom `incoming_inspection` model) to a single custom model:

- **Model**: `repair_helpdesk.incoming_inspection` with `repair_helpdesk.incoming_inspection.line`
- **Creation**: Created manually via "Create Inspection Checklist" button on the ticket (when in "Received / Initial Inspection" stage).
- **3 fixed sub-checks**: Drop damage, Water damage or corrosion, Excessive contamination. Each line has `result` (pass/fail/na), `comment`, and `image` (Binary, attachment=True).
- **Fail enforcement**: If `result == 'fail'`, both `comment` and `image` are required (enforced via `@api.constrains`).
- **Completion** (`action_done`): All pass/na → ticket moves to "Ready for Repair". Any fail → create `quality.alert`, post message, hold stage. Failed inspections can be overridden via "Approve for Repair" (requires reason note) which also moves ticket to "Ready for Repair".
- **Stage gate**: "Complete Inspection" button only works when the ticket is in "Received / Initial Inspection" stage (`ticket_in_inspection_stage` computed field).
- **Repair gate**: "Create Repair Order" button requires the ticket to be in "Ready for Repair" stage AND inspection completed AND (no failures OR repair_approved).
- **Images**: Stored as `fields.Binary(attachment=True)` — automatically stored as `ir.attachment` records.
- **Alerts**: `quality` is still in `depends` for creating `quality.alert` records on inspection failures.
- **Quotation from repair**: When creating a sale order from `repair.order`, the context carries the ticket ID. The created quotation is auto-linked to the helpdesk ticket, enabling stage transitions on send/confirm.

### Flow

```
Ticket → Create incoming picking → Validate picking →
  Technician creates inspection → Fills checklist →
  Complete → pass: Ready for Repair / fail: alert + hold
    → Ready for Repair → Create Repair → Diagnostics
    → Revise Quotation → Waiting for revised approval
```

## Git conventions

- **Branches**: `19.0-develop` (base), `19.0-develop-<module>` (feature)
- **Commits**: lowercase, sometimes prefixed (`feat:`, `fix:`, `refactor:`)
