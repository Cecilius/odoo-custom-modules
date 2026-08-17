# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class RfbLabel(models.Model):
    _name = 'resale.rfb.label'
    _description = 'RFB Label'
    _order = 'category_code, sequence'

    category_id = fields.Many2one('resale.category', string='Category', required=True)
    category_code = fields.Char(related='category_id.code', store=True, string='Category Code')
    sequence = fields.Integer(string='Sequence', required=True)
    rfb = fields.Char(string='RFB', compute='_compute_rfb', store=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('reprint', 'Reprint Requested'),
        ('void', 'Void'),
    ], string='Status', default='available')
    item_id = fields.Many2one('resale.item', string='Item', readonly=True)
    print_batch = fields.Char(string='Print Batch')
    print_count = fields.Integer(string='Print Count', default=0)
    last_print_date = fields.Datetime(string='Last Print')
    reprint_reason = fields.Char(string='Reprint Reason')

    @api.depends('category_code', 'sequence')
    def _compute_rfb(self):
        for label in self:
            label.rfb = 'RFB-%s-%06d' % (label.category_code, label.sequence)

    _label_uniq = models.Constraint(
        'unique(category_code, sequence)',
        'RFB label must be unique per category.',
    )
