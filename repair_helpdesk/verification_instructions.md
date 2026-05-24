# Repair Helpdesk Verification Instructions

This document explains how to verify the repair helpdesk quality and location integration.

## 1. Update and install the module

From the repository root:

```bash
cd /Users/bambito/GIT/odoo-enterprise
./odoo-bin -c /path/to/odoo.conf -d <your_db> -u repair_helpdesk
```

Replace `/path/to/odoo.conf` with your actual Odoo configuration file and `<your_db>` with the target database.

## 2. Run the verification script

From the repository root, execute:

```bash
python3 odoo-custom-modules/repair_helpdesk/verify_repair_helpdesk.py -d <your_db> -c /path/to/odoo.conf
```

Expected output:
- `repair_helpdesk installed: True`
- `Found quality inspection points: 5`
- `stock.picking.helpdesk_ticket_id field exists: True`
- `quality.check.picking_id field exists: True`
- `Found repair routes: 2`
- all repair locations exist

## 3. Manual verification steps

### 3.1 Create a repair ticket
1. Open the Helpdesk app.
2. Create a new ticket with a customer and device description.
3. Save the ticket.

### 3.2 Create and validate an incoming shipment
1. On the ticket, create the incoming picking.
2. Confirm the created picking opens directly in form view.
3. Validate the picking.
4. Verify a `quality.check` record was created for each incoming inspection point.
   - Drop damage
   - Water damage
   - Contamination
   - Accessories
   - Visible damages

### 3.3 Confirm inspection outcomes
1. Open the created quality checks from the Picking or Quality app.
2. Set each check to `pass` or `fail` as appropriate.
3. If all checks pass, confirm the ticket stage updates to `Awaiting item`.
4. If any check fails, confirm a `quality.alert` is created and the ticket receives a note.

### 3.4 Verify repair location data
1. Open Inventory > Locations.
2. Confirm these locations exist:
   - Repair Workshop
   - Incoming Inspection Location
   - Awaiting Repair Location
   - Repair In Progress Location
   - Quality Control / Awaiting Shipment
   - Repair Return Dispatch
3. Open Inventory > Routes and confirm these routes exist:
   - Repair Incoming Inspection Flow
   - Repair Return Dispatch Flow

### 3.5 Validate stock route structure
1. Open each repair route.
2. Confirm it has at least one rule linking the expected source and destination locations.

## 4. Optional deep verification

If you want to verify the full flow in Odoo shell:

```bash
cd /Users/bambito/GIT/odoo-enterprise
./odoo-bin shell -d <your_db> -c /path/to/odoo.conf
```

Then run:

```python
Ticket = env['helpdesk.ticket']
Picking = env['stock.picking']
QualityCheck = env['quality.check']

# sample counts
print(Ticket.search_count([]))
print(Picking.search_count([('helpdesk_ticket_id', '!=', False)]))
print(QualityCheck.search_count([('picking_id.helpdesk_ticket_id', '!=', False)]))
```

## 5. Notes

- The verification script assumes the Odoo codebase is at `odoo-enterprise/odoo` relative to the module.
- If you use a different config path, pass it with `-c`.
- If the script cannot import Odoo, make sure your Python environment includes the required Odoo dependencies.
