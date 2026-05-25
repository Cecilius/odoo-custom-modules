from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
    ticket_in_inspection_stage = fields.Boolean(
        string='Ticket in Initial Inspection Stage',
        compute='_compute_ticket_stage_flags',
    )

    @api.depends('helpdesk_ticket_id.stage_id')
    def _compute_ticket_stage_flags(self):
        initial_stage = self.env.ref('repair_helpdesk.stage_repair_initial_inspection', raise_if_not_found=False)
        for inspection in self:
            inspection.ticket_in_inspection_stage = bool(
                initial_stage
                and inspection.helpdesk_ticket_id
                and inspection.helpdesk_ticket_id.stage_id == initial_stage
            )

    @api.model_create_multi
    def create(self, vals_list):
        if not vals_list:
            return super().create(vals_list)
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('repair_helpdesk.incoming_inspection') or 'New'
        inspections = super().create(vals_list)
        for inspection in inspections:
            if not inspection.line_ids:
                inspection._create_default_lines()
        return inspections

    def _create_default_lines(self):
        default_items = [
            'Drop damage',
            'Water damage or corrosion',
            'Excessive contamination',
        ]
        lines = [(0, 0, {'name': item, 'sequence': i + 1}) for i, item in enumerate(default_items)]
        self.write({'line_ids': lines})

    def action_done(self):
        self.ensure_one()
        if self.status == 'done':
            return
        if not self.ticket_in_inspection_stage:
            raise UserError(_(
                'Inspection can only be completed when the ticket is in the '
                '"Received / Initial Inspection" stage.'
            ))
        if not self.line_ids:
            raise UserError(_('Please fill in the checklist items before completing the inspection.'))
        unset_lines = self.line_ids.filtered(lambda l: not l.result)
        if unset_lines:
            raise UserError(_('All checklist items must have a result before completing the inspection.'))
        self.status = 'done'
        ticket = self.helpdesk_ticket_id
        failed_lines = self.line_ids.filtered(lambda l: l.result == 'fail')
        if failed_lines:
            self._handle_inspection_failed(ticket, failed_lines)
        else:
            self._handle_inspection_passed(ticket)

    def action_reset_to_draft(self):
        self.ensure_one()
        if self.status != 'done':
            raise UserError(_('Only completed inspections can be reset to draft.'))
        self.status = 'draft'
        self.helpdesk_ticket_id.message_post(
            body=_('Incoming inspection %s was reset to draft.') % self.name
        )

    def _handle_inspection_passed(self, ticket):
        ticket._set_stage('repair_helpdesk.stage_repair_diagnostics')
        ticket.message_post(
            body=_('Incoming inspection %s completed. All checks passed. Ticket moved to Diagnostics.') % self.name
        )

    def _handle_inspection_failed(self, ticket, failed_lines):
        failed_names = ', '.join(failed_lines.mapped('name'))
        failed_details = '\n'.join(
            '%s: %s' % (line.name, line.comment)
            for line in failed_lines
        )
        alert_team = self.env.ref('quality.quality_alert_team0', raise_if_not_found=False) or self.env['quality.alert.team'].search([], limit=1)
        self.env['quality.alert'].create({
            'name': _('Incoming inspection failure: %s') % self.name,
            'team_id': alert_team.id,
            'company_id': alert_team.company_id.id or self.env.company.id,
            'description': _(
                'The following checks failed during incoming inspection %(inspection)s for ticket %(ticket)s:\n'
                '%(items)s\n\n'
                'Comments:\n'
                '%(details)s\n\n'
                'Customer should be contacted to decide whether to proceed with repair or return the device. '
                'Fees may apply in case of rejection.'
            ) % {
                'inspection': self.name,
                'ticket': ticket.display_name,
                'items': failed_names,
                'details': failed_details,
            },
        })
        ticket.message_post(
            body=_(
                'Incoming inspection %(inspection)s completed with failures: %(items)s. '
                'Quality alert created. Customer should be contacted before proceeding.'
            ) % {
                'inspection': self.name,
                'items': failed_names,
            }
        )


class RepairHelpdeskIncomingInspectionLine(models.Model):
    _name = 'repair_helpdesk.incoming_inspection.line'
    _description = 'Repair Helpdesk Incoming Inspection Checklist Item'
    _order = 'sequence, id'

    inspection_id = fields.Many2one(
        'repair_helpdesk.incoming_inspection',
        string='Inspection',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Checklist Item', required=True)
    result = fields.Selection(
        [('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A')],
        string='Result',
    )
    comment = fields.Text(string='Comment')
    image = fields.Binary(string='Picture', attachment=True)

    @api.constrains('result', 'comment', 'image')
    def _check_fail_requirements(self):
        for line in self:
            if line.result == 'fail':
                if not line.comment:
                    raise UserError(_('A comment is required when "%s" is marked as failed.') % line.name)
                if not line.image:
                    raise UserError(_('A picture is required when "%s" is marked as failed.') % line.name)
