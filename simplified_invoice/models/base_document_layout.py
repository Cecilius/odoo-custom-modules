from odoo import fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    # Make the company tax identification number available in the
    # document layout preview and in the shared external footer template.
    company_registry = fields.Char(related='company_id.company_registry', readonly=True)