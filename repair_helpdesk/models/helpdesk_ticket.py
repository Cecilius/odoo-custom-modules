from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    sale_order_id = fields.Many2one('sale.order', string='Quotation / Sales Order', copy=False)
    repair_order_id = fields.Many2one('repair.order', string='Repair Order', copy=False)
    x_device_description = fields.Char(string='Device / Model')
    x_serial_number = fields.Char(string='Serial Number')
    x_reported_issue = fields.Text(string='Reported Issue')
    x_is_repair_ticket = fields.Boolean(
        string='Repair Ticket',
        compute='_compute_repair_workflow_flags',
        store=False,
    )
    x_can_create_quotation = fields.Boolean(
        compute='_compute_repair_workflow_flags',
        store=False,
    )
    x_can_open_quotation = fields.Boolean(
        compute='_compute_repair_workflow_flags',
        store=False,
    )
    x_can_create_repair_order = fields.Boolean(
        compute='_compute_repair_workflow_flags',
        store=False,
    )
    x_can_open_repair_order = fields.Boolean(
        compute='_compute_repair_workflow_flags',
        store=False,
    )

    @api.depends('team_id', 'team_id.x_repair_workflow_team', 'stage_id', 'sale_order_id', 'repair_order_id')
    def _compute_repair_workflow_flags(self):
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
        quotation_stage_ids = self._stage_ids_from_xmlids(quotation_stage_xmlids)
        repair_stage_ids = self._stage_ids_from_xmlids(repair_stage_xmlids)

        for ticket in self:
            is_repair = bool(ticket.team_id and ticket.team_id.x_repair_workflow_team)
            stage_id = ticket.stage_id.id if ticket.stage_id else False
            ticket.x_is_repair_ticket = is_repair
            ticket.x_can_create_quotation = bool(is_repair and not ticket.sale_order_id and stage_id in quotation_stage_ids)
            ticket.x_can_open_quotation = bool(is_repair and ticket.sale_order_id)
            ticket.x_can_create_repair_order = bool(is_repair and not ticket.repair_order_id and stage_id in repair_stage_ids)
            ticket.x_can_open_repair_order = bool(is_repair and ticket.repair_order_id)

    def _stage_ids_from_xmlids(self, xmlids):
        ids = set()
        for xmlid in xmlids:
            record = self.env.ref(xmlid, raise_if_not_found=False)
            if record:
                ids.add(record.id)
        return ids

    def _set_stage(self, xmlid):
        self.ensure_one()
        stage = self.env.ref(xmlid, raise_if_not_found=False)
        if stage:
            self.stage_id = stage.id

    def _get_default_sales_team(self):
        sales_team = self.env['crm.team'].search([('active', '=', True)], limit=1)
        if not sales_team:
            raise UserError(_('Please configure at least one active Sales Team before creating a quotation.'))
        return sales_team

    def _get_default_diagnostic_product(self):
        return self.env.ref('repair_helpdesk.product_diagnostic_fee_others', raise_if_not_found=False)

    def action_create_quotation(self):
        self.ensure_one()
        if not self.x_can_create_quotation:
            raise UserError(_('Quotation creation is not available in the current stage or the ticket already has a quotation.'))
        if not self.partner_id:
            raise UserError(_('Please set a customer on the ticket before creating a quotation.'))

        shipping_product = self.env.ref('repair_helpdesk.product_return_shipping', raise_if_not_found=False)
        diagnostic_product = self._get_default_diagnostic_product()
        sales_team = self._get_default_sales_team()

        order_lines = []
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
        if shipping_product:
            order_lines.append((0, 0, {
                'product_id': shipping_product.id,
                'name': shipping_product.get_product_multiline_description_sale() or shipping_product.name,
                'product_uom_qty': 1.0,
                'price_unit': shipping_product.list_price,
            }))

        order_vals = {
            'partner_id': self.partner_id.id,
            'team_id': sales_team.id,
            'origin': self.ticket_ref or self.name,
            'client_order_ref': self.ticket_ref or self.name,
            'note': self.description or _('Created from Helpdesk repair ticket.'),
            'order_line': order_lines,
        }
        quotation = self.env['sale.order'].create(order_vals)
        self.sale_order_id = quotation.id
        self.message_post(body=_('Quotation %s created.') % quotation.name)
        self._set_stage('repair_helpdesk.stage_repair_quote_approval')
        return self.action_open_quotation()

    def action_open_quotation(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_('No quotation linked to this ticket.'))
        action = self.env.ref('sale.action_quotations').read()[0]
        action.update({
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        })
        return action

    def action_create_repair_order(self):
        self.ensure_one()
        if not self.x_can_create_repair_order:
            raise UserError(_('Repair order creation is not available in the current stage or the ticket already has a repair order.'))
        if not self.partner_id:
            raise UserError(_('Please set a customer on the ticket before creating a repair order.'))

        vals = {
            'partner_id': self.partner_id.id,
            'product_qty': 1.0,
            'name': self.ticket_ref or self.name,
            'under_warranty': False,
        }
        if 'lot_name' in self.env['repair.order']._fields and self.x_serial_number:
            vals['lot_name'] = self.x_serial_number
        if 'description' in self.env['repair.order']._fields:
            vals['description'] = self.x_reported_issue or self.description
        repair_order = self.env['repair.order'].create(vals)
        self.repair_order_id = repair_order.id
        self.message_post(body=_('Repair order %s created.') % (getattr(repair_order, 'name', _('(draft)'))))
        self._set_stage('repair_helpdesk.stage_repair_initial_inspection')
        return self.action_open_repair_order()

    def action_open_repair_order(self):
        self.ensure_one()
        if not self.repair_order_id:
            raise UserError(_('No repair order linked to this ticket.'))
        action = self.env.ref('repair.action_repair_order').read()[0]
        action.update({
            'res_id': self.repair_order_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        })
        return action
