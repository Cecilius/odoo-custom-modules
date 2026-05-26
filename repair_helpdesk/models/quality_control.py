from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class RepairHelpdeskQualityControl(models.Model):
    _name = 'repair_helpdesk.quality_control'
    _description = 'Repair Helpdesk Quality Control'

    name = fields.Char(string='QC Reference', required=True, copy=False, default='New')
    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Customer', related='helpdesk_ticket_id.partner_id', readonly=True, store=True)
    ticket_ref = fields.Char(string='Ticket Reference', related='helpdesk_ticket_id.ticket_ref', readonly=True, store=True)
    device_description = fields.Char(string='Device Description', related='helpdesk_ticket_id.x_device_description', readonly=True, store=True)
    serial_number = fields.Char(string='Serial Number', related='helpdesk_ticket_id.x_serial_number', readonly=True, store=True)
    qc_note = fields.Text(string='QC Notes')
    status = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done')],
        string='Status',
        default='draft',
    )
    line_ids = fields.One2many(
        'repair_helpdesk.quality_control.line',
        'qc_id',
        string='Checklist Items',
        copy=True,
    )
    general_image_ids = fields.One2many(
        'repair_helpdesk.quality_control.image',
        'qc_id',
        string='General Pictures',
        copy=True,
    )
    inspection_id = fields.Many2one(
        'repair_helpdesk.incoming_inspection',
        string='Initial Inspection',
        compute='_compute_inspection_ref',
        readonly=True,
        store=True,
    )
    inspection_summary = fields.Text(
        string='Initial Inspection Summary',
        compute='_compute_inspection_ref',
        readonly=True,
    )
    inspection_image_ids = fields.One2many(
        'repair_helpdesk.incoming_inspection.image',
        'inspection_id',
        string='Inspection Pictures',
        compute='_compute_inspection_image_ids',
        readonly=True,
    )

    @api.depends('helpdesk_ticket_id.inspection_ids')
    def _compute_inspection_ref(self):
        for qc in self:
            inspections = qc.helpdesk_ticket_id.inspection_ids
            insp = inspections.sorted('id', reverse=True)[:1]
            qc.inspection_id = insp if inspections else False
            if insp:
                lines = '\n'.join(
                    '  %s: %s' % (line.name, dict(line._fields['result'].selection).get(line.result, '-'))
                    for line in insp.line_ids
                )
                issue = qc.helpdesk_ticket_id.x_reported_issue or ''
                confirmed = dict(
                    insp._fields['reported_fault_confirmed'].selection
                ).get(insp.reported_fault_confirmed, '-') if insp.reported_fault_confirmed else '-'
                qc.inspection_summary = _(
                    'Reported issue: %(issue)s\n'
                    'Fault confirmed: %(confirmed)s\n'
                    'Checklist:\n%(lines)s'
                ) % {
                    'issue': issue or '(not specified)',
                    'confirmed': confirmed,
                    'lines': lines or '(no checklist items)',
                }
            else:
                qc.inspection_summary = False

    @api.depends('inspection_id')
    def _compute_inspection_image_ids(self):
        for qc in self:
            qc.inspection_image_ids = (
                qc.inspection_id.general_image_ids
                if qc.inspection_id
                else self.env['repair_helpdesk.incoming_inspection.image']
            )

    @api.model_create_multi
    def create(self, vals_list):
        if not vals_list:
            return super().create(vals_list)
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('repair_helpdesk.quality_control') or 'New'
        qcs = super().create(vals_list)
        for qc in qcs:
            if not qc.line_ids:
                qc._create_default_lines()
            qc._post_inspection_to_chatter()
        return qcs

    def _post_inspection_to_chatter(self):
        insp = self.inspection_id
        if not insp:
            return
        lines = []
        for line in insp.line_ids:
            result_label = dict(line._fields['result'].selection).get(line.result, '-')
            line_text = '%s: %s' % (line.name, result_label)
            if line.comment:
                line_text += '\n    Comment: %s' % line.comment
            lines.append(line_text)
        body = _('Initial Inspection %s Summary:\n\n') % insp.name
        body += '\n'.join(lines)
        if insp.reported_fault_confirmed:
            confirmed = dict(insp._fields['reported_fault_confirmed'].selection).get(insp.reported_fault_confirmed, '-')
            body += '\n\nFault confirmed: %s' % confirmed
        if insp.reported_fault_notes:
            body += '\n\nFault diagnosis: %s' % insp.reported_fault_notes
        self.message_post(body=body)

    def _create_default_lines(self):
        default_items = [
            'Overall condition / New damage',
            'Reported fault repaired',
            'Device cleaned',
        ]
        lines = [(0, 0, {'name': item, 'sequence': i + 1}) for i, item in enumerate(default_items)]
        self.write({'line_ids': lines})

    def action_done(self):
        self.ensure_one()
        if self.status == 'done':
            return
        if not self.line_ids:
            raise UserError(_('Please fill in the checklist items before completing the QC.'))
        unset_lines = self.line_ids.filtered(lambda l: not l.result)
        if unset_lines:
            raise UserError(_('All checklist items must have a result before completing the QC.'))
        self.status = 'done'
        ticket = self.helpdesk_ticket_id
        failed_lines = self.line_ids.filtered(lambda l: l.result == 'fail')
        if failed_lines:
            self._handle_qc_failed(ticket, failed_lines)
        else:
            self._handle_qc_passed(ticket)

    def _handle_qc_passed(self, ticket):
        ticket._set_stage('repair_helpdesk.stage_repair_finished')
        ticket.message_post(
            body=_('Quality control %s completed. All checks passed.') % self.name
        )

    def _handle_qc_failed(self, ticket, failed_lines):
        failed_names = ', '.join(failed_lines.mapped('name'))
        failed_details = '\n'.join(
            '%s: %s' % (line.name, line.comment)
            for line in failed_lines
        )
        alert_team = self.env.ref('quality.quality_alert_team0', raise_if_not_found=False) or self.env['quality.alert.team'].search([], limit=1)
        self.env['quality.alert'].create({
            'name': _('Quality control failure: %s') % self.name,
            'team_id': alert_team.id,
            'company_id': alert_team.company_id.id or self.env.company.id,
            'description': _(
                'The following checks failed during quality control %(qc)s for ticket %(ticket)s:\n'
                '%(items)s\n\n'
                'Comments:\n'
                '%(details)s'
            ) % {
                'qc': self.name,
                'ticket': ticket.display_name,
                'items': failed_names,
                'details': failed_details,
            },
        })
        repair = self.env['repair.order'].create({
            'partner_id': ticket.partner_id.id,
            'product_qty': 1.0,
            'name': ticket.ticket_ref or ticket.name,
            'helpdesk_ticket_id': ticket.id,
            'under_warranty': False,
            'description': _('Rework for QC failures: %s') % failed_names,
        })
        ticket._set_stage('repair_helpdesk.stage_repair_under_repair')
        ticket.message_post(
            body=_(
                'Quality control %(qc)s completed with failures: %(items)s. '
                'New repair order %(repair)s created. Ticket moved to Under Repair.'
            ) % {
                'qc': self.name,
                'items': failed_names,
                'repair': repair.name,
            }
        )


class RepairHelpdeskQualityControlLine(models.Model):
    _name = 'repair_helpdesk.quality_control.line'
    _description = 'Repair Helpdesk Quality Control Checklist Item'
    _order = 'sequence, id'

    qc_id = fields.Many2one(
        'repair_helpdesk.quality_control',
        string='Quality Control',
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
                    raise ValidationError(_('A comment is required when "%s" is marked as failed.') % line.name)
                if not line.image:
                    raise ValidationError(_('A picture is required when "%s" is marked as failed.') % line.name)
