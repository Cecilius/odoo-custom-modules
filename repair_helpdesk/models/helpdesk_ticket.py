from odoo import _, fields, models
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    sale_order_id = fields.Many2one('sale.order', string='Quotation / Sales Order', copy=False)
    repair_order_id = fields.Many2one('repair.order', string='Repair Order', copy=False)
    x_device_description = fields.Char(string='Device / Model')
    x_serial_number = fields.Char(string='Serial Number')
    x_is_repair_ticket = fields.Boolean(
        string='Repair Ticket',
        compute='_compute_x_is_repair_ticket',
        store=False,
    )

    def _compute_x_is_repair_ticket(self):
        for ticket in self:
            ticket.x_is_repair_ticket = bool(ticket.team_id and getattr(ticket.team_id, 'x_repair_workflow_team', False))

    def action_create_quotation(self):
        self.ensure_one()
        if self.sale_order_id:
            return self.action_open_quotation()
        if not self.partner_id:
            raise UserError(_('Please set a customer on the ticket before creating a quotation.'))

        shipping_product = self.env.ref('repair_helpdesk.product_return_shipping', raise_if_not_found=False)
        order_vals = {
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'client_order_ref': self.ticket_ref or self.name,
            'note': _('Return shipping is included in this estimate and will only be charged if the device is returned by courier/post. It will be removed in case of in-person pickup.'),
            'order_line': [],
        }
        if shipping_product:
            order_vals['order_line'].append((0, 0, {
                'product_id': shipping_product.id,
                'name': shipping_product.get_product_multiline_description_sale() or shipping_product.name,
                'product_uom_qty': 1.0,
                'price_unit': shipping_product.list_price,
            }))
        quotation = self.env['sale.order'].create(order_vals)
        self.sale_order_id = quotation.id
        self.message_post(body=_('Quotation %s created.') % quotation.name)
        return self.action_open_quotation()

    def action_open_quotation(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_('No quotation linked to this ticket.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quotation'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
            'target': 'current',
        }

    def action_create_repair_order(self):
        self.ensure_one()
        if self.repair_order_id:
            return self.action_open_repair_order()
        if not self.partner_id:
            raise UserError(_('Please set a customer on the ticket before creating a repair order.'))

        vals = {
            'partner_id': self.partner_id.id,
            'product_id': False,
            'product_qty': 1.0,
            'name': self.name,
            'under_warranty': False,
        }
        if 'lot_name' in self.env['repair.order']._fields and self.x_serial_number:
            vals['lot_name'] = self.x_serial_number
        repair_order = self.env['repair.order'].create(vals)
        self.repair_order_id = repair_order.id
        self.message_post(body=_('Repair order created.'))
        return self.action_open_repair_order()

    def action_open_repair_order(self):
        self.ensure_one()
        if not self.repair_order_id:
            raise UserError(_('No repair order linked to this ticket.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Repair Order'),
            'res_model': 'repair.order',
            'view_mode': 'form',
            'res_id': self.repair_order_id.id,
            'target': 'current',
        }
