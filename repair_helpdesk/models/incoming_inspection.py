from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class RepairHelpdeskIncomingInspection(models.Model):
    _name = 'repair_helpdesk.incoming_inspection'
    _inherit = ['mail.thread']
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
    ticket_in_qc_stage = fields.Boolean(
        string='Ticket in QC Stage',
        compute='_compute_ticket_stage_flags',
    )
    repair_approved = fields.Boolean(string='Approved for Repair', default=False)
    repair_approve_note = fields.Text(string='Approval Reason')
    has_failures = fields.Boolean(
        string='Has Failures',
        compute='_compute_has_failures',
        store=True,
    )
    customer_reported_drop = fields.Selection(
        related='helpdesk_ticket_id.x_reported_drop_damage',
        readonly=True,
    )
    customer_reported_water = fields.Selection(
        related='helpdesk_ticket_id.x_reported_water_damage',
        readonly=True,
    )
    customer_reported_contamination = fields.Selection(
        related='helpdesk_ticket_id.x_reported_contamination',
        readonly=True,
    )
    customer_reported_issue = fields.Text(
        related='helpdesk_ticket_id.x_reported_issue',
        readonly=True,
    )
    reported_fault_confirmed = fields.Selection(
        [('yes', 'Yes - fault found'), ('no', 'No - fault not found'), ('partial', 'Partial - symptoms exist but different cause')],
        string='Reported Fault Confirmed',
    )
    reported_fault_notes = fields.Text(string='Fault Diagnosis Notes')
    qc_status = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done')],
        string='QC Status',
        default='draft',
    )
    qc_note = fields.Text(string='QC Notes')
    qc_line_ids = fields.One2many(
        'repair_helpdesk.incoming_inspection.qc_line',
        'inspection_id',
        string='QC Checklist Items',
        copy=True,
    )

    @api.depends('helpdesk_ticket_id.stage_id')
    def _compute_ticket_stage_flags(self):
        initial_stage = self.env.ref('repair_helpdesk.stage_repair_initial_inspection', raise_if_not_found=False)
        qc_stage = self.env.ref('repair_helpdesk.stage_repair_qc', raise_if_not_found=False)
        for inspection in self:
            inspection.ticket_in_inspection_stage = bool(
                initial_stage
                and inspection.helpdesk_ticket_id
                and inspection.helpdesk_ticket_id.stage_id == initial_stage
            )
            inspection.ticket_in_qc_stage = bool(
                qc_stage
                and inspection.helpdesk_ticket_id
                and inspection.helpdesk_ticket_id.stage_id == qc_stage
            )

    @api.depends('line_ids.result')
    def _compute_has_failures(self):
        for inspection in self:
            inspection.has_failures = any(
                line.result == 'fail' for line in inspection.line_ids
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

    def _create_default_qc_lines(self):
        default_items = [
            'Overall condition / New damage',
            'Reported fault repaired',
            'Device cleaned',
        ]
        lines = [(0, 0, {'name': item, 'sequence': i + 1}) for i, item in enumerate(default_items)]
        self.write({'qc_line_ids': lines})

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
        self.repair_approved = False
        self.helpdesk_ticket_id.message_post(
            body=_('Incoming inspection %s was reset to draft.') % self.name
        )

    def action_approve_for_repair(self):
        self.ensure_one()
        if self.status != 'done':
            raise UserError(_('Only completed inspections can be approved for repair.'))
        if not self.has_failures:
            raise UserError(_('This inspection has no failures — approval is not required.'))
        if not self.repair_approve_note:
            raise UserError(_('Please enter an approval reason before approving this failed inspection for repair.'))
        self.repair_approved = True
        self.helpdesk_ticket_id._set_stage('repair_helpdesk.stage_repair_ready_for_repair')
        self.helpdesk_ticket_id.message_post(
            body=_('Incoming inspection %s approved for repair:\n%s') % (self.name, self.repair_approve_note)
        )

    def action_qc_done(self):
        self.ensure_one()
        if self.qc_status == 'done':
            return
        if not self.ticket_in_qc_stage:
            raise UserError(_('QC can only be completed when the ticket is in the "Quality control" stage.'))
        if not self.qc_line_ids:
            raise UserError(_('Please fill in the QC checklist items before completing the QC.'))
        unset_lines = self.qc_line_ids.filtered(lambda l: not l.result)
        if unset_lines:
            raise UserError(_('All QC checklist items must have a result before completing the QC.'))
        self.qc_status = 'done'
        ticket = self.helpdesk_ticket_id
        failed_lines = self.qc_line_ids.filtered(lambda l: l.result == 'fail')
        if failed_lines:
            self._handle_qc_failed(ticket, failed_lines)
        else:
            self._handle_qc_passed(ticket)

    def _handle_inspection_passed(self, ticket):
        ticket._set_stage('repair_helpdesk.stage_repair_ready_for_repair')
        ticket.message_post(
            body=_('Incoming inspection %s completed. All checks passed.') % self.name
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

    def _handle_qc_passed(self, ticket):
        ticket._set_stage('repair_helpdesk.stage_repair_finished')
        for repair in ticket.repair_order_ids.filtered(lambda r: r.state == 'qc'):
            repair.state = 'done'
            repair.message_post(body=_('Quality control passed. All checks OK.'))
        ticket.message_post(
            body=_('Quality control %s completed. All checks passed.') % self.name
        )

    def _handle_qc_failed(self, ticket, failed_lines):
        failed_names = ', '.join(failed_lines.mapped('name'))
        result_labels = dict(self.qc_line_ids._fields['result'].selection)
        note_text = 'QC Notes: %s' % self.qc_note if self.qc_note else ''
        lines_br = '<br/>'.join(
            '%s: %s%s' % (
                line.name,
                result_labels.get(line.result, '-'),
                ' - %s' % line.comment if line.comment else '',
            )
            for line in self.qc_line_ids
        )
        lines_nl = '\n'.join(
            '%s: %s%s' % (
                line.name,
                result_labels.get(line.result, '-'),
                ' - %s' % line.comment if line.comment else '',
            )
            for line in self.qc_line_ids
        )
        alert_summary = 'QC failed - Rework required\n%s\n%s' % (
            note_text, lines_nl,
        ) if note_text else 'QC failed - Rework required\n%s' % lines_nl
        chat_summary = '<b>QC failed - Rework required</b><br/>%s%s' % (
            '<b>%s</b><br/>' % note_text if note_text else '',
            lines_br,
        )
        alert_team = self.env.ref('quality.quality_alert_team0', raise_if_not_found=False) or self.env['quality.alert.team'].search([], limit=1)
        self.env['quality.alert'].create({
            'name': _('Quality control failure: %s') % self.name,
            'team_id': alert_team.id,
            'company_id': alert_team.company_id.id or self.env.company.id,
            'description': alert_summary,
        })
        self.message_post(body=chat_summary)
        for repair in ticket.repair_order_ids.filtered(lambda r: r.state == 'qc'):
            repair.state = 'under_repair'
            repair.message_post(body=chat_summary)
        ticket._set_stage('repair_helpdesk.stage_repair_under_repair')
        ticket.message_post(
            body=_(
                'Quality control %(qc)s completed with failures: %(items)s. '
                'Repair reopened for rework. Ticket moved to Under Repair.'
            ) % {
                'qc': self.name,
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

    @api.constrains('result', 'comment')
    def _check_fail_requirements(self):
        for line in self:
            if line.result == 'fail' and not line.comment:
                raise ValidationError(_('A comment is required when "%s" is marked as failed.') % line.name)


class RepairHelpdeskIncomingInspectionQcLine(models.Model):
    _name = 'repair_helpdesk.incoming_inspection.qc_line'
    _description = 'Repair Helpdesk Incoming Inspection QC Checklist Item'
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

    @api.constrains('result', 'comment')
    def _check_fail_requirements(self):
        for line in self:
            if line.result == 'fail' and not line.comment:
                raise ValidationError(_('A comment is required when "%s" is marked as failed.') % line.name)
