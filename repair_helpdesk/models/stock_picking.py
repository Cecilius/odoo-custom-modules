from odoo import fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    helpdesk_ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string='Helpdesk Ticket',
        copy=False,
        index=True,
    )

    def _create_quality_check_for_incoming(self):
        self.ensure_one()
        if self.picking_type_code != 'incoming' or not self.helpdesk_ticket_id:
            return

        quality_point_model = self.env['quality.point']
        quality_check_model = self.env['quality.check']
        quality_points = quality_point_model.search([
            ('picking_type_ids', 'in', self.picking_type_id.id),
            ('active', '=', True),
        ])
        if not quality_points:
            return

        existing_point_ids = quality_check_model.search([('picking_id', '=', self.id)]).mapped('point_id.id')
        checks_to_create = []
        for point in quality_points.filtered(lambda p: p.id not in existing_point_ids):
            vals = {
                'point_id': point.id,
                'picking_id': self.id,
            }
            if self.move_lines:
                product = self.move_lines[0].product_id
                if product and product.type == 'consu':
                    vals['product_id'] = product.id
            checks_to_create.append(vals)

        if not checks_to_create:
            return

        quality_check_model.create(checks_to_create)
        self.helpdesk_ticket_id.message_post(
            body=_('Quality inspection was added for incoming shipment %s.') % self.name
        )

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals:
            done_pickings = self.filtered(lambda p: p.state == 'done' and p.helpdesk_ticket_id)
            for picking in done_pickings:
                if picking.picking_type_code == 'incoming':
                    picking._create_quality_check_for_incoming()
                    picking.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_initial_inspection')
                elif picking.picking_type_code == 'outgoing':
                    picking.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_closed')
        return res

    def _action_done(self):
        res = super()._action_done()
        done_pickings = self.filtered(lambda p: p.state == 'done' and p.helpdesk_ticket_id)
        for picking in done_pickings:
            if picking.picking_type_code == 'incoming':
                picking._create_quality_check_for_incoming()
                picking.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_initial_inspection')
            elif picking.picking_type_code == 'outgoing':
                picking.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_closed')
        return res
