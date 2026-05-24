from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    # Reverse links from sale orders to the ticket.
    # We use One2many because in the future a ticket may have more than one quotation
    # (for example, a revised quotation or a replacement commercial document).
    sale_order_ids = fields.One2many(
        'sale.order',
        'helpdesk_ticket_id',
        string='Quotations / Sales Orders',
    )

    # Reverse links from repair orders to the ticket.
    # Even if today we expect one repair order in most cases, One2many keeps the design flexible.
    repair_order_ids = fields.One2many(
        'repair.order',
        'helpdesk_ticket_id',
        string='Repair Orders',
    )

    # Shipment / logistics links.
    picking_ids = fields.One2many(
        'stock.picking',
        'helpdesk_ticket_id',
        string='Shipments',
    )
    incoming_picking_ids = fields.One2many(
        'stock.picking',
        'helpdesk_ticket_id',
        string='Incoming Shipments',
        domain=[('picking_type_code', '=', 'incoming')],
    )
    outgoing_picking_ids = fields.One2many(
        'stock.picking',
        'helpdesk_ticket_id',
        string='Outgoing Shipments',
        domain=[('picking_type_code', '=', 'outgoing')],
    )

    picking_count = fields.Integer(
        string='Shipment Count',
        compute='_compute_related_counts',
    )
    incoming_picking_count = fields.Integer(
        string='Incoming Shipment Count',
        compute='_compute_related_counts',
    )
    outgoing_picking_count = fields.Integer(
        string='Outgoing Shipment Count',
        compute='_compute_related_counts',
    )

    x_carrier_name = fields.Char(string='Carrier')
    x_tracking_reference = fields.Char(string='Tracking Reference')

    # Counts displayed in smart buttons.
    sale_order_count = fields.Integer(
        string='Quotation Count',
        compute='_compute_related_counts',
    )
    repair_order_count = fields.Integer(
        string='Repair Order Count',
        compute='_compute_related_counts',
    )

    # Operational fields used by the repair workflow.
    x_device_description = fields.Char(string='Device / Model')
    x_serial_number = fields.Char(string='Serial Number')
    x_reported_issue = fields.Text(string='Reported Issue')

    # Helper flag: true only for tickets that belong to the repair workflow team.
    x_is_repair_ticket = fields.Boolean(
        string='Repair Ticket',
        compute='_compute_repair_workflow_flags',
        store=False,
    )

    # Helper flags used by XML to show / hide the creation buttons.
    # Keeping this logic in Python makes the view much cleaner.
    x_can_create_quotation = fields.Boolean(
        string='Can Create Quotation',
        compute='_compute_repair_workflow_flags',
        store=False,
    )
    x_can_create_repair_order = fields.Boolean(
        string='Can Create Repair Order',
        compute='_compute_repair_workflow_flags',
        store=False,
    )
    x_can_create_incoming_picking = fields.Boolean(
        string='Can Create Incoming Shipment',
        compute='_compute_repair_workflow_flags',
        store=False,
    )
    x_can_create_outgoing_picking = fields.Boolean(
        string='Can Create Outgoing Shipment',
        compute='_compute_repair_workflow_flags',
        store=False,
    )

    @api.depends('sale_order_ids', 'repair_order_ids', 'incoming_picking_ids', 'outgoing_picking_ids', 'picking_ids')
    def _compute_related_counts(self):
        """Compute smart-button counters for linked commercial and repair documents."""
        for ticket in self:
            ticket.sale_order_count = len(ticket.sale_order_ids)
            ticket.repair_order_count = len(ticket.repair_order_ids)
            ticket.picking_count = len(ticket.picking_ids)
            ticket.incoming_picking_count = len(ticket.incoming_picking_ids)
            ticket.outgoing_picking_count = len(ticket.outgoing_picking_ids)

    @api.depends(
        'team_id',
        'team_id.x_repair_workflow_team',
        'stage_id',
        'sale_order_ids',
        'repair_order_ids',
        'incoming_picking_ids',
        'outgoing_picking_ids',
    )
    def _compute_repair_workflow_flags(self):
        """Control which workflow buttons are visible on the ticket.

        The visibility rules are based on:
        - whether the ticket belongs to the dedicated repair team,
        - the current helpdesk stage,
        - whether a quotation or repair order already exists.
        """
        quotation_stage_xmlids = {
            'repair_helpdesk.stage_repair_new',
            'repair_helpdesk.stage_repair_quote_approval',
            'repair_helpdesk.stage_repair_revised_approval',
        }
        repair_stage_xmlids = {
            'repair_helpdesk.stage_repair_awaiting_item',
            'repair_helpdesk.stage_repair_initial_inspection',
            'repair_helpdesk.stage_repair_diagnostics',
            'repair_helpdesk.stage_repair_under_repair',
            'repair_helpdesk.stage_repair_waiting_parts',
            'repair_helpdesk.stage_repair_qc',
            'repair_helpdesk.stage_repair_payment',
            'repair_helpdesk.stage_repair_ready_return',
        }
        incoming_shipment_stage_xmlids = {'repair_helpdesk.stage_repair_awaiting_item'}
        outgoing_shipment_stage_xmlids = {'repair_helpdesk.stage_repair_ready_return'}

        quotation_stage_ids = self._stage_ids_from_xmlids(quotation_stage_xmlids)
        repair_stage_ids = self._stage_ids_from_xmlids(repair_stage_xmlids)
        incoming_stage_ids = self._stage_ids_from_xmlids(incoming_shipment_stage_xmlids)
        outgoing_stage_ids = self._stage_ids_from_xmlids(outgoing_shipment_stage_xmlids)

        for ticket in self:
            is_repair = bool(ticket.team_id and ticket.team_id.x_repair_workflow_team)
            current_stage_id = ticket.stage_id.id if ticket.stage_id else False

            ticket.x_is_repair_ticket = is_repair
            ticket.x_can_create_quotation = bool(
                is_repair
                and not ticket.sale_order_ids
                and current_stage_id in quotation_stage_ids
            )
            ticket.x_can_create_repair_order = bool(
                is_repair
                and not ticket.repair_order_ids
                and current_stage_id in repair_stage_ids
            )
            ticket.x_can_create_incoming_picking = bool(
                is_repair
                and current_stage_id in incoming_stage_ids
                and not ticket.incoming_picking_ids
            )
            ticket.x_can_create_outgoing_picking = bool(
                is_repair
                and current_stage_id in outgoing_stage_ids
                and not ticket.outgoing_picking_ids
            )

    def _stage_ids_from_xmlids(self, xmlids):
        """Resolve a set of XML IDs into existing stage record IDs.

        Missing XML IDs are ignored, which keeps the compute method resilient.
        """
        ids = set()
        for xmlid in xmlids:
            record = self.env.ref(xmlid, raise_if_not_found=False)
            if record:
                ids.add(record.id)
        return ids

    def _set_stage(self, xmlid):
        """Move the ticket to a target stage if that stage exists."""
        self.ensure_one()
        stage = self.env.ref(xmlid, raise_if_not_found=False)
        if stage:
            self.stage_id = stage.id

    def _get_default_sales_team(self):
        """Find an active sales team to use when generating a quotation.

        Later this can be replaced by a dedicated repair sales team configuration.
        """
        sales_team = self.env['crm.team'].search([('active', '=', True)], limit=1)
        if not sales_team:
            raise UserError(_('Please configure at least one active Sales Team before creating a quotation.'))
        return sales_team

    def _get_default_diagnostic_product(self):
        """Return the default diagnostic service product used on the initial quotation."""
        return self.env.ref('repair_helpdesk.product_diagnostic_fee_others', raise_if_not_found=False)

    def _get_incoming_pickings_for_outgoing(self):
        """Return the incoming pickings used to prefill outgoing shipment products."""
        return self.incoming_picking_ids.filtered(lambda p: p.state == 'done')

    def _prepare_outgoing_moves(self, incoming_pickings, picking_type):
        """Build outgoing move values based on incoming shipment products."""
        moves = []
        if not incoming_pickings:
            return moves

        for move in incoming_pickings.mapped('move_ids').filtered(lambda m: m.state != 'cancel'):
            moves.append((0, 0, {
                'description_picking': move.description_picking or move.product_id.name,
                'product_id': move.product_id.id,
                'product_uom_qty': move.product_uom_qty,
                'product_uom': move.product_uom.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'company_id': self.env.company.id,
            }))
        return moves

    def _get_default_picking_type(self, code):
        """Return the default incoming or outgoing picking type for the current company."""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', code),
            ('active', '=', True),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', code),
                ('active', '=', True),
            ], limit=1)
        if not picking_type:
            raise UserError(_(
                'Please configure an active %s picking type before creating shipments.'
            ) % code.capitalize())
        return picking_type

    def action_create_incoming_picking(self):
        """Create an incoming shipment linked to the repair ticket."""
        self.ensure_one()
        if not self.x_can_create_incoming_picking:
            raise UserError(_('Incoming shipment creation is not available in the current stage.'))
        if not self.partner_id:
            raise UserError(_('Please set a customer on the ticket before creating an incoming shipment.'))

        picking_type = self._get_default_picking_type('incoming')
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'origin': self.ticket_ref or self.name,
            'partner_id': self.partner_id.id,
            'helpdesk_ticket_id': self.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'note': _('Incoming shipment for repair ticket %s') % self.display_name,
        })

        self.message_post(body=_('Incoming shipment %s created.') % picking.name)
        return self.action_view_shipments()

    def action_create_outgoing_picking(self):
        """Create an outgoing shipment linked to the repair ticket."""
        self.ensure_one()
        if not self.x_can_create_outgoing_picking:
            raise UserError(_('Outgoing shipment creation is not available in the current stage.'))
        if not self.partner_id:
            raise UserError(_('Please set a customer on the ticket before creating an outgoing shipment.'))

        picking_type = self._get_default_picking_type('outgoing')
        incoming_pickings = self._get_incoming_pickings_for_outgoing()
        if not incoming_pickings:
            raise UserError(_('Please create and validate an incoming shipment before creating an outgoing shipment.'))

        move_lines = self._prepare_outgoing_moves(incoming_pickings, picking_type)
        picking_vals = {
            'picking_type_id': picking_type.id,
            'origin': self.ticket_ref or self.name,
            'partner_id': self.partner_id.id,
            'helpdesk_ticket_id': self.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'note': _('Outgoing shipment for repair ticket %s') % self.display_name,
        }
        if move_lines:
            picking_vals['move_ids'] = move_lines

        picking = self.env['stock.picking'].create(picking_vals)

        self.message_post(body=_('Outgoing shipment %s created.') % picking.name)
        self._set_stage('repair_helpdesk.stage_repair_ready_return')
        return self.action_view_shipments()

    def action_view_shipments(self):
        """Open linked shipments.

        - If only one document exists, open it directly in form view.
        - If several exist, open a filtered list view.
        """
        self.ensure_one()

        if self.picking_count == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Shipment'),
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': self.picking_ids[:1].id,
                'target': 'current',
            }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipments'),
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('helpdesk_ticket_id', '=', self.id)],
            'context': {'default_helpdesk_ticket_id': self.id},
            'target': 'current',
        }

    def _prepare_quotation_note(self):
        """Build the default internal / customer-facing note for the quotation."""
        self.ensure_one()
        return _(
            'This quotation was created from Helpdesk ticket %(ticket)s.\n'
            'Return shipping is included in this estimate and will only be charged '
            'if the device is returned by courier/post. It will be removed in case of in-person pickup.'
        ) % {
            'ticket': self.display_name,
        }

    def action_create_quotation(self):
        """Create a draft quotation linked back to the helpdesk ticket.

        Important workflow note:
        - creating a quotation does NOT move the ticket to waiting for approval;
        - the ticket should move there only when the quotation is actually sent.
        That second step is handled in the sale.order extension.
        """
        self.ensure_one()

        if not self.x_can_create_quotation:
            raise UserError(_('Quotation creation is not available in the current stage or the ticket already has a quotation.'))

        if not self.partner_id:
            raise UserError(_('Please set a customer on the ticket before creating a quotation.'))

        shipping_product = self.env.ref('repair_helpdesk.product_return_shipping', raise_if_not_found=False)
        diagnostic_product = self._get_default_diagnostic_product()
        sales_team = self._get_default_sales_team()

        order_lines = []

        # First quotation line: default diagnostic / estimate service.
        if diagnostic_product:
            description = diagnostic_product.get_product_multiline_description_sale() or diagnostic_product.name
            if self.x_device_description:
                description = '%s\n%s: %s' % (description, _('Device'), self.x_device_description)
            if self.x_reported_issue:
                description = '%s\n%s: %s' % (description, _('Issue'), self.x_reported_issue)

            order_lines.append((0, 0, {
                'product_id': diagnostic_product.id,
                'name': description,
                'product_uom_qty': 1.0,
                'price_unit': diagnostic_product.list_price,
            }))

        # Second quotation line: return shipping, removable later if the customer chooses pickup.
        if shipping_product:
            order_lines.append((0, 0, {
                'product_id': shipping_product.id,
                'name': shipping_product.get_product_multiline_description_sale() or shipping_product.name,
                'product_uom_qty': 1.0,
                'price_unit': shipping_product.list_price,
            }))

        quotation = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'team_id': sales_team.id,
            'helpdesk_ticket_id': self.id,
            'origin': self.ticket_ref or self.name,
            'client_order_ref': self.ticket_ref or self.name,
            'note': self._prepare_quotation_note(),
            'order_line': order_lines,
        })

        self.message_post(body=_('Quotation %s created.') % quotation.name)

        # Do NOT move to quotation approval here.
        # The quotation is still only a draft at this point.
        return self.action_view_sale_orders()

    def action_create_repair_order(self):
        """Create a repair order linked back to the ticket.

        Once a repair order exists, the ticket moves to the initial inspection stage.
        """
        self.ensure_one()

        if not self.x_can_create_repair_order:
            raise UserError(_('Repair order creation is not available in the current stage or the ticket already has a repair order.'))

        if not self.partner_id:
            raise UserError(_('Please set a customer on the ticket before creating a repair order.'))

        vals = {
            'partner_id': self.partner_id.id,
            'product_qty': 1.0,
            'name': self.ticket_ref or self.name,
            'helpdesk_ticket_id': self.id,
            'under_warranty': False,
        }

        # Fill serial number when the repair model supports lot_name.
        if 'lot_name' in self.env['repair.order']._fields and self.x_serial_number:
            vals['lot_name'] = self.x_serial_number

        # Fill description when the repair model supports it.
        if 'description' in self.env['repair.order']._fields:
            vals['description'] = self.x_reported_issue or self.description

        repair_order = self.env['repair.order'].create(vals)
        self.message_post(body=_('Repair order %s created.') % (getattr(repair_order, 'name', _('(draft)'))))

        # After the repair order is created, the workshop can start intake / initial inspection.
        self._set_stage('repair_helpdesk.stage_repair_initial_inspection')
        return self.action_view_repair_orders()

    def action_view_sale_orders(self):
        """
        Opens the sale.order tree view with a domain to show only 'Draft' orders
        and a context to set a default salesperson.
        """
        return {
            'name': "Draft Sales Orders",
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'tree,form', # You can specify 'tree' if you only want the tree view
            'domain': [('state', '=', 'draft')], # Filter for sales orders in 'Draft' state
            'context': {
                'default_user_id': self.env.user.id, # Sets the current user as the default salesperson
                'search_default_my_draft_filter': 1, # Example: Activates a predefined search filter (if one exists)
                'some_custom_key': 'some_value', # Another example of a custom context key
            },
            'target': 'current', # 'current' opens in the main content area, 'new' opens in a dialog
        }

    def action_view_repair_orders(self):
        """Open linked repair orders.

        - If only one record exists, open it directly in form view.
        - If several exist, open a filtered list view.
        """
        self.ensure_one()

        if self.repair_order_count == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Repair Order'),
                'res_model': 'repair.order',
                'view_mode': 'form',
                'res_id': self.repair_order_ids[:1].id,
                'target': 'current',
            }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Repair Orders'),
            'res_model': 'repair.order',
            'view_mode': 'tree,form',
            'domain': [('helpdesk_ticket_id', '=', self.id)],
            'context': {'default_helpdesk_ticket_id': self.id},
            'target': 'current',
        }
