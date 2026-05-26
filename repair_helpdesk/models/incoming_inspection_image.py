from odoo import fields, models


class IncomingInspectionImage(models.Model):
    _name = 'repair_helpdesk.incoming_inspection.image'
    _description = 'Incoming Inspection General Image'
    _order = 'sequence, id'

    inspection_id = fields.Many2one(
        'repair_helpdesk.incoming_inspection',
        string='Inspection',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    image = fields.Binary(string='Picture', attachment=True)
    description = fields.Char(string='Description')


class QualityControlImage(models.Model):
    _name = 'repair_helpdesk.quality_control.image'
    _description = 'Quality Control General Image'
    _order = 'sequence, id'

    qc_id = fields.Many2one(
        'repair_helpdesk.quality_control',
        string='Quality Control',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    image = fields.Binary(string='Picture', attachment=True)
    description = fields.Char(string='Description')
