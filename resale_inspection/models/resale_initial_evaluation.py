# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class InitialEvaluation(models.Model):
    _name = 'resale.initial.evaluation'
    _inherit = ['mail.thread']
    _description = 'Initial Evaluation'
    _rec_name = 'name'

    name = fields.Char(string='Reference', default='New', copy=False)
    item_id = fields.Many2one('resale.item', string='Item', required=True,
                              ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='Operator',
                              default=lambda self: self.env.user, required=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)

    condition_id = fields.Many2one('resale.condition', string='Condition Estimate')
    functional_status = fields.Selection(related='item_id.functional_status')
    completeness = fields.Selection(related='item_id.completeness')
    basic_result = fields.Selection([
        ('pass', 'Basic test passed'),
        ('fault', 'Basic fault found'),
        ('unable', 'Unable to test'),
    ], string='Basic Test Result', required=True)
    disposition = fields.Selection([
        ('sale', 'Potentially ready for sale'),
        ('test', 'Needs detailed testing'),
        ('repair', 'Needs repair'),
        ('dismantling', 'Needs dismantling'),
        ('scrap', 'Scrap review'),
        ('hold', 'Hold'),
    ], string='Initial Disposition', required=True)
    comment = fields.Text(string='Comment')
    image_ids = fields.Many2many('ir.attachment', string='Photos')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'resale.initial.evaluation') or 'New'
        return super().create(vals_list)
