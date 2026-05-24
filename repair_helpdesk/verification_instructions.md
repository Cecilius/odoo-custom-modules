# Repair Helpdesk Verification Instructions

This document explains how to verify the repair helpdesk quality and location integration.

## 1. Update and install the module

From the repository root:

```bash
cd /Users/bambito/GIT/odoo-enterprise
./odoo-bin -c /path/to/odoo.conf -d <your_db> -u repair_helpdesk
```

Replace `/path/to/odoo.conf` with your actual Odoo configuration file and `<your_db>` with the target database.

## 2. Manual verification (preferred)

The verification can be performed entirely through the Odoo user interface. This is usually faster and avoids environment-specific setup required by the Python script. Follow the steps in section 3 below to exercise the full flow:

- Create a Helpdesk ticket and customer/device record
- Create the associated incoming picking from the ticket and open it in form view
- Validate the incoming picking and confirm `quality.check` records were created for each inspection point
- Perform `pass`/`fail` on each quality check and observe ticket stage and alerts
- Verify repair-only locations and routes exist under Inventory > Locations / Routes

Note: an optional automation script (`verify_repair_helpdesk.py`) still exists in the repository for environments where running Odoo from the command line is convenient. The script requires a working Odoo Python environment and may need the `--odoo-root` parameter for non-standard installations (CloudPepper). If you prefer automated checks, the script can be used; otherwise, skip it and follow the manual steps above.

## 3. Manual verification steps

### 3.1 Create a repair ticket
1. Open the Helpdesk app.
2. Create a new ticket with a customer and device description.
3. Save the ticket.

### 3.2 Create and validate an incoming shipment
1. On the ticket, create the incoming picking.
2. Confirm the created picking opens directly in form view.
3. Validate the picking.
4. Verify that a single incoming inspection `quality.check` record was created for the shipment.
   - The check should cover drop damage, water damage, contamination, accessories, and visible cosmetic issues.

> Note: the current implementation creates one combined `quality.check` record for incoming inspection. This simplifies the workflow and keeps all inspection findings in one place.

### 3.3 Confirm inspection outcomes
1. Open the created quality checks from the Picking or Quality app.
2. Set each check to `pass` or `fail` as appropriate.
3. If all checks pass, confirm the ticket stage updates to `Diagnostics`.
4. If any check fails, confirm a `quality.alert` is created and the ticket receives a note.

> Why it should not go back: `Awaiting item` is the stage before receiving the product. After inspection passes, the ticket should move forward into diagnostics, not backward.
>
> On failure: the current flow records a failure alert and notes the ticket. The next step is a manual business decision: inform the customer, decide whether to continue repair, return the item, or apply storage/shipping fees. That customer-decision process is best handled outside this core inspection automation.



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

> Note: these locations and routes are created automatically when `repair_helpdesk` is installed or upgraded, because `repair_locations.xml` is included in the module data. If you do not see them after installation, verify that the module is installed and that Inventory/Stock is active in the system.


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

- The verification script assumes the Odoo codebase is at `odoo-enterprise/` relative to the module by default.
- For CloudPepper or other custom infrastructure, use the `--odoo-root` parameter to specify your actual Odoo installation path.
- Common Odoo root paths on CloudPepper:
  - `/opt/odoo/` (if using standard CloudPepper layout)
  - `/home/odoo/server/` (alternative path)
  - Check your CloudPepper configuration for the exact location
- If you use a different config path, pass it with `-c`.
- If the script cannot import Odoo, verify:
  - The `--odoo-root` path is correct
  - Your Python environment includes the required Odoo dependencies
  - The configuration file path is correct
