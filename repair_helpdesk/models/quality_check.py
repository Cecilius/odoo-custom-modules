from odoo import api, fields, models, _


class QualityCheck(models.Model):
    _inherit = 'quality.check'

    def write(self, vals):
        if self.env.context.get('repair_helpdesk_skip_quality_result_hook'):
            return super().write(vals)

        old_states = {check.id: check.quality_state for check in self}
        with_context = dict(self.env.context, repair_helpdesk_skip_quality_result_hook=True)
        res = super(QualityCheck, self.with_context(**with_context)).write(vals)

        changed_checks = self.filtered(
            lambda check: check.quality_state != old_states.get(check.id)
        )
        if changed_checks:
            changed_checks._process_repair_helpdesk_quality_result()

        return res

    def _process_repair_helpdesk_quality_result(self):
        for check in self:
            picking = check.picking_id
            ticket = picking.helpdesk_ticket_id
            if not ticket:
                continue

            if check.quality_state == 'pass':
                all_passed = picking.check_ids and all(
                    qc.quality_state == 'pass'
                    for qc in picking.check_ids
                )
                if all_passed:
                    ticket._set_stage('repair_helpdesk.stage_repair_awaiting_item')
                    ticket.message_post(
                        body=_('All incoming inspection checks passed for shipment %s. Ticket moved to Awaiting item.') % picking.name
                    )
            elif check.quality_state == 'fail':
                alert_model = self.env['quality.alert']
                if not alert_model.search([('check_id', '=', check.id)], limit=1):
                    alert_model.create({
                        'name': _('Inspection failure: %s') % check.name,
                        'check_id': check.id,
                        'picking_id': picking.id,
                        'team_id': check.team_id.id,
                        'company_id': check.company_id.id,
                        'description': _(
                            'Inspection point %s has failed for shipment %s. Review the device and determine corrective action.'
                        ) % (check.name, picking.name),
                    })
                ticket.message_post(
                    body=_('Inspection failure recorded for shipment %s: %s') % (picking.name, check.name)
                )
