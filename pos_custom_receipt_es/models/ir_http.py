# pos_custom_receipt_es/models/ir_http.py
from odoo import models

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        modules = super()._get_translation_frontend_modules_name()
        # Add our POS receipt module so its JS/QWeb translations are sent to the frontend
        return modules + ['pos_custom_receipt_es']