from odoo import models


class AcquisitionBatch(models.Model):
    _inherit = 'resale.acquisition.batch'

    def action_open_ai_intake(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'AI Item Intake',
            'res_model': 'resale.ai.intake.wizard',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_batch_id': self.id},
        }
