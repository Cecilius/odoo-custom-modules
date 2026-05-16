from odoo import fields, models


class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    x_repair_workflow_team = fields.Boolean(string='Repair Workflow Team', default=False)
