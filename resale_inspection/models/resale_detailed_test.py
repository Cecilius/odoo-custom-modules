# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DetailedTest(models.Model):
    _name = 'resale.detailed.test'
    _inherit = ['mail.thread']
    _description = 'Detailed Test'
    _order = 'date desc'

    name = fields.Char(string='Reference', default='New', copy=False)
    item_id = fields.Many2one('resale.item', string='Item', required=True,
                              ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='Tester',
                              default=lambda self: self.env.user, required=True)
    date = fields.Datetime(string='Completion Date', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Completed'),
    ], string='Status', default='draft', tracking=True)

    test_type_id = fields.Many2one('resale.test.type', string='Test Type')
    result = fields.Selection([
        ('pass', 'Test completed - no fault noted'),
        ('fault', 'Test completed - fault found'),
        ('unable', 'Unable to test'),
    ], string='Result', required=True)

    final_condition_id = fields.Many2one('resale.condition', string='Final Condition')
    final_functional_status = fields.Selection([
        ('working', 'Working'),
        ('repairable', 'Not working but easy to repair'),
        ('unknown', 'Unknown'),
        ('uncertain', 'Repair uncertain'),
        ('not_working', 'Not working'),
        ('parts_only', 'Tested for parts only'),
    ], string='Final Functional Status')
    final_disposition = fields.Selection([
        ('pricing', 'Ready for pricing'),
        ('repair', 'Needs repair'),
        ('dismantling', 'Needs dismantling'),
        ('scrap', 'Scrap'),
        ('hold', 'Hold'),
    ], string='Final Disposition', required=True)

    comment = fields.Text(string='Comment')
    attachment_ids = fields.Many2many('ir.attachment', string='Evidence')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'resale.detailed.test') or 'New'
        return super().create(vals_list)

    def _item_state_from_disposition(self):
        self.ensure_one()
        return {
            'pricing': 'pricing',
            'repair': 'needs_repair',
            'dismantling': 'needs_dismantling',
            'scrap': 'scrapped',
            'hold': 'hold',
        }.get(self.final_disposition, 'detailed_test')

    def action_complete(self):
        """Persist final test data and update the item's workflow state."""
        for test in self:
            if test.state == 'done':
                continue
            if not test.result:
                raise UserError(_('Please select a test result.'))
            if not test.final_disposition:
                raise UserError(_('Please select a final disposition.'))
            test.item_id.write({
                'condition_id': test.final_condition_id.id,
                'functional_status': test.final_functional_status,
                'state': test._item_state_from_disposition(),
            })
            test.write({
                'state': 'done',
                'date': fields.Datetime.now(),
            })
        return True
