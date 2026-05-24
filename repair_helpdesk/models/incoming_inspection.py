from odoo import api, fields, models, _


class RepairHelpdeskIncomingInspection(models.Model):
    _name = 'repair_helpdesk.incoming_inspection'
    _description = 'Repair Helpdesk Incoming Inspection'

    name = fields.Char(string='Inspection Reference', required=True, copy=False, default='New')
    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Customer', related='helpdesk_ticket_id.partner_id', readonly=True, store=True)
    ticket_ref = fields.Char(string='Ticket Reference', related='helpdesk_ticket_id.ticket_ref', readonly=True, store=True)
    device_description = fields.Char(string='Device Description', related='helpdesk_ticket_id.x_device_description', readonly=True, store=True)
    serial_number = fields.Char(string='Serial Number', related='helpdesk_ticket_id.x_serial_number', readonly=True, store=True)
    inspection_note = fields.Text(string='Inspection Notes')
    status = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done')],
        string='Status',
        default='draft',
    )
    line_ids = fields.One2many(
        'repair_helpdesk.incoming_inspection.line',
        'inspection_id',
        string='Checklist Items',
        copy=True,
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('repair_helpdesk.incoming_inspection') or 'New'
        inspection = super().create(vals)
        if not inspection.line_ids:
            inspection._create_default_lines()
        return inspection

    def _create_default_lines(self):
        default_items = [
            'Device condition / cosmetics',
            'Water damage or corrosion',
            'Contamination / dirt / debris',
            'Accessories and documentation present',
            'Visible damage, scratches, dents, cracks',
        ]
        lines = [(0, 0, {'name': name, 'result': 'pass'}) for name in default_items]
        self.write({'line_ids': lines})


class RepairHelpdeskIncomingInspectionLine(models.Model):
    _name = 'repair_helpdesk.incoming_inspection.line'
    _description = 'Repair Helpdesk Incoming Inspection Checklist Item'

    inspection_id = fields.Many2one(
        'repair_helpdesk.incoming_inspection',
        string='Inspection',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Checklist Item', required=True)
    result = fields.Selection(
        [('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A')],
        string='Result',
        default='pass',
        required=True,
    )
    comment = fields.Text(string='Comment')
