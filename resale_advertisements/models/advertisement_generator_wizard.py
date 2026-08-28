import json
import re

from odoo import _, api, fields, models
from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.exceptions import UserError


class ResaleAdvertisementGenerator(models.TransientModel):
    _name = 'resale.advertisement.generator'
    _description = 'AI Description Generator'

    product_template_id = fields.Many2one(
        'product.template', required=True, ondelete='cascade',
    )
    max_characters = fields.Integer(string='Max characters', default=2000)
    research_info = fields.Text(string='Information sent to AI', readonly=True)
    error_message = fields.Text(string='Status', readonly=True)
    proposal_1 = fields.Text(string='Proposal 1')
    proposal_2 = fields.Text(string='Proposal 2')
    proposal_3 = fields.Text(string='Proposal 3')
    state = fields.Selection(
        [('draft', 'Ready'), ('confirm_overwrite', 'Confirm Overwrite'),
         ('proposals', 'Proposals'), ('error', 'Error')],
        default='draft', required=True,
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        if not vals.get('max_characters'):
            raw = self.env['ir.config_parameter'].sudo().get_param(
                'resale_advertisement.max_characters', '2000'
            )
            try:
                vals['max_characters'] = max(int(raw), 1)
            except (TypeError, ValueError):
                vals['max_characters'] = 2000
        product = self.env['product.template'].browse(
            self.env.context.get('default_product_template_id')
        )
        if product:
            vals['research_info'] = self._build_context_text(product)
        return vals

    def _get_agent(self, key):
        value = self.env['ir.config_parameter'].sudo().get_param(key)
        return self.env['ai.agent'].browse(int(value)).exists() if value and value.isdigit() else self.env['ai.agent']

    def _build_context_text(self, product):
        resale = product.resale_product_id
        lines = []
        if resale:
            lines.append('Product name: %s' % (resale.name or ''))
            lines.append('EAN: %s' % (resale.ean or ''))
            lines.append('UPC: %s' % (resale.upc or ''))
            lines.append('ASIN: %s' % (resale.asin or ''))
            if resale.brand_value_id:
                lines.append('Brand: %s' % resale.brand_value_id.name)
            if resale.category_id:
                lines.append('Category: %s' % resale.category_id.display_name)
            if resale.description:
                lines.append('Product description: %s' % resale.description)
        else:
            lines.append('Product name: %s' % (product.name or ''))
        test = product.resale_product_test_ids[:1]
        if test:
            lines.append('Most recent product test result: %s' % (test.result_id.name or ''))
            if test.notes:
                lines.append('Test notes: %s' % test.notes)
        return '\n'.join(line for line in lines if line)

    def action_generate(self):
        self.ensure_one()
        if self.product_template_id.description_ecommerce:
            self.state = 'confirm_overwrite'
            self.error_message = _(
                'This product already has a description. Continuing will generate new '
                'proposals and the one you choose will overwrite the current description.'
            )
            return self._reload()
        return self._run_generation()

    def action_confirm_generate(self):
        self.ensure_one()
        return self._run_generation()

    def _run_generation(self):
        self.ensure_one()
        context_text = self._build_context_text(self.product_template_id)
        self.research_info = context_text
        agent = self._get_agent('resale_advertisement.research_agent_id')
        if not agent:
            raise UserError(_('Configure a listing research agent in Settings first.'))
        try:
            with self.env.cr.savepoint():
                result = self._ask_agent(agent, context_text)
        except Exception as primary_error:
            backup = self._get_agent('resale_advertisement.backup_agent_id')
            if not backup or backup == agent:
                self.state = 'error'
                self.error_message = _('The listing research agent failed: %s') % primary_error
                return self._reload()
            try:
                with self.env.cr.savepoint():
                    result = self._ask_agent(backup, context_text)
            except Exception as backup_error:
                self.state = 'error'
                self.error_message = _(
                    'Both research agents failed. Primary: %(primary)s. Backup: %(backup)s.'
                ) % {'primary': primary_error, 'backup': backup_error}
                return self._reload()
            self.error_message = _('The primary agent was unavailable; the backup agent response is shown.')

        proposals = result.get('proposals') or []
        if not proposals:
            proposals = [result.get('proposal_%d' % i) for i in range(1, 4)]
            proposals = [proposal for proposal in proposals if proposal]
        if not proposals:
            self.state = 'error'
            self.error_message = _('The AI agent did not return any proposal.')
            return self._reload()

        proposals = [str(proposal).strip() for proposal in proposals[:3]]
        while len(proposals) < 3:
            proposals.append('')
        self.proposal_1 = proposals[0]
        self.proposal_2 = proposals[1]
        self.proposal_3 = proposals[2]
        self.state = 'proposals'
        return self._reload()

    def _ask_agent(self, agent, context_text):
        max_chars = self.max_characters or 2000
        schema = {
            'type': 'object',
            'properties': {
                'proposals': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'minItems': 3,
                    'maxItems': 3,
                },
            },
            'required': ['proposals'],
        }
        prompt = _(
            'Generate 3 distinct, ready-to-publish product descriptions for the product '
            'below, intended for resale marketplaces. Each description must be a self-contained '
            'description highlighting the product\'s key features, condition, and selling points. '
            'Each proposal must differ in style and wording. '
            'Each proposal must not exceed %(max_chars)s characters. '
            'Return ONLY one valid JSON object with a "proposals" array of exactly 3 strings. '
            'Do not include Markdown fences, comments, or any other text.\n'
            'Product information:\n%(context)s'
        ) % {'max_chars': max_chars, 'context': context_text}
        provider = agent._get_provider()
        service = LLMApiService(self.env, provider=provider)
        response = service.request_llm(
            agent.llm_model,
            [agent.system_prompt or 'You are an expert e-commerce copywriter.'],
            [prompt],
            schema=schema if provider != 'google' else None,
            web_grounding=agent.web_search,
        )
        raw = response[-1] if response else ''
        self.error_message = False
        try:
            result = json.loads(re.sub(r'^```(?:json)?|```$', '', raw.strip(), flags=re.MULTILINE).strip())
            if result.get('candidates'):
                text = result['candidates'][0]['content']['parts'][0].get('text', '')
                result = json.loads(text)
            return result
        except (TypeError, ValueError) as error:
            raise UserError(_('The AI agent returned an invalid structured response.')) from error

    def _apply_proposal(self, text):
        self.ensure_one()
        if not text:
            raise UserError(_('The selected proposal is empty.'))
        max_chars = self.max_characters or 0
        if max_chars and len(text) > max_chars:
            text = text[:max_chars]
        escaped = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        html = '<p>%s</p>' % escaped.replace('\n', '<br/>')
        self.product_template_id.description_ecommerce = html
        return {'type': 'ir.actions.act_window_close'}

    def action_use_proposal_1(self):
        return self._apply_proposal(self.proposal_1)

    def action_use_proposal_2(self):
        return self._apply_proposal(self.proposal_2)

    def action_use_proposal_3(self):
        return self._apply_proposal(self.proposal_3)

    def _reload(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
