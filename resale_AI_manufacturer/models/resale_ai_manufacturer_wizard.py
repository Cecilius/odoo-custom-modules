import json
import re

from odoo import _, api, fields, models
from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.exceptions import UserError


class ResaleAIManufacturerWizard(models.TransientModel):
    _name = 'resale.ai.manufacturer.wizard'
    _description = 'AI GPSR Manufacturer & Compliance Finder'

    resale_product_id = fields.Many2one(
        'resale.product', required=True, ondelete='cascade',
    )
    product_display = fields.Text(string='Product information sent to AI', readonly=True)
    state = fields.Selection(
        [('draft', 'Ready'), ('result', 'Result'), ('error', 'Error'), ('done', 'Done')],
        default='draft', required=True,
    )
    error_message = fields.Text(string='Status', readonly=True)

    # Manufacturer (proposed by AI)
    m_name = fields.Char(string='Name')
    m_street = fields.Char(string='Street')
    m_city = fields.Char(string='City')
    m_zip = fields.Char(string='ZIP')
    m_country_id = fields.Many2one('res.country', string='Country')
    m_email = fields.Char(string='Email')
    m_phone = fields.Char(string='Phone')
    m_website = fields.Char(string='Website')
    manufacturer_candidate_ids = fields.Many2many(
        'res.partner', string='Similar existing contacts',
        relation='resale_ai_mfr_manufacturer_rel',
        column1='wizard_id', column2='partner_id',
    )
    manufacturer_use_partner_id = fields.Many2one(
        'res.partner', string='Use existing contact',
        domain="[('id', 'in', manufacturer_candidate_ids)]",
    )
    manufacturer_action = fields.Selection(
        [('create', 'Create as new contact'),
         ('use_existing', 'Use suggested existing contact'),
         ('skip', 'Skip')],
        string='Manufacturer action', default='create',
    )
    manufacturer_note = fields.Text(string='Recommendation', readonly=True)

    # EU Responsible person (proposed by AI)
    r_name = fields.Char(string='Name')
    r_street = fields.Char(string='Street')
    r_city = fields.Char(string='City')
    r_zip = fields.Char(string='ZIP')
    r_country_id = fields.Many2one('res.country', string='Country')
    r_email = fields.Char(string='Email')
    r_phone = fields.Char(string='Phone')
    r_website = fields.Char(string='Website')
    eu_responsible_candidate_ids = fields.Many2many(
        'res.partner', string='Similar existing contacts',
        relation='resale_ai_mfr_eu_responsible_rel',
        column1='wizard_id', column2='partner_id',
    )
    eu_responsible_use_partner_id = fields.Many2one(
        'res.partner', string='Use existing contact',
        domain="[('id', 'in', eu_responsible_candidate_ids)]",
    )
    eu_responsible_action = fields.Selection(
        [('create', 'Create as new contact'),
         ('use_existing', 'Use suggested existing contact'),
         ('skip', 'Skip')],
        string='EU Responsible action', default='create',
    )
    eu_responsible_note = fields.Text(string='Recommendation', readonly=True)

    ce_compliance = fields.Text(string='CE Compliance')
    safety_record = fields.Text(string='Safety Record')
    same_company_note = fields.Text(string='Same company check', readonly=True)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        product = self.env['resale.product'].browse(
            self.env.context.get('default_resale_product_id')
        )
        if product:
            vals['product_display'] = self._build_context_text(product)
        return vals

    def _get_agent(self, key):
        value = self.env['ir.config_parameter'].sudo().get_param(key)
        return self.env['ai.agent'].browse(int(value)).exists() if value and value.isdigit() else self.env['ai.agent']

    @staticmethod
    def _build_context_text(product):
        lines = [
            'Name: %s' % (product.name or ''),
            'EAN: %s' % (product.ean or ''),
            'UPC: %s' % (product.upc or ''),
            'ASIN: %s' % (product.asin or ''),
        ]
        if product.brand_value_id:
            lines.append('Brand: %s' % product.brand_value_id.name)
        return '\n'.join(line for line in lines if line)

    def action_generate(self):
        self.ensure_one()
        agent = self._get_agent('resale_ai_manufacturer.research_agent_id')
        if not agent:
            raise UserError(_('Configure a GPSR research agent in Settings first.'))
        context_text = self._build_context_text(self.resale_product_id)
        self.product_display = context_text
        try:
            with self.env.cr.savepoint():
                result = self._ask_agent(agent, context_text)
        except Exception as primary_error:
            backup = self._get_agent('resale_ai_manufacturer.backup_agent_id')
            if not backup or backup == agent:
                self.state = 'error'
                self.error_message = _('The GPSR research agent failed: %s') % primary_error
                return self._reload()
            try:
                with self.env.cr.savepoint():
                    result = self._ask_agent(backup, context_text)
            except Exception as backup_error:
                self.state = 'error'
                self.error_message = _(
                    'Both GPSR research agents failed. Primary: %(primary)s. Backup: %(backup)s.'
                ) % {'primary': primary_error, 'backup': backup_error}
                return self._reload()
            self.error_message = _('The primary agent was unavailable; the backup agent response is shown.')

        self._apply_result(result)
        self.state = 'result'
        return self._reload()

    def _ask_agent(self, agent, context_text):
        schema = {
            'type': 'object',
            'properties': {
                'manufacturer': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'}, 'street': {'type': 'string'},
                        'city': {'type': 'string'}, 'zip': {'type': 'string'},
                        'country': {'type': 'string'}, 'email': {'type': 'string'},
                        'phone': {'type': 'string'}, 'website': {'type': 'string'},
                    },
                    'required': ['name'],
                },
                'eu_responsible': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'}, 'street': {'type': 'string'},
                        'city': {'type': 'string'}, 'zip': {'type': 'string'},
                        'country': {'type': 'string'}, 'email': {'type': 'string'},
                        'phone': {'type': 'string'}, 'website': {'type': 'string'},
                    },
                    'required': ['name'],
                },
                'ce_compliance': {'type': 'string'},
                'safety_record': {'type': 'string'},
            },
            'required': ['manufacturer', 'eu_responsible', 'ce_compliance', 'safety_record'],
        }
        prompt = _(
            'Research this product using web search to find GPSR (General Product Safety '
            'Regulation) compliance information. Never invent details; use null/empty for anything unknown.\n'
            'Return ONLY one valid JSON object with the structure below. Do not include Markdown '
            'fences, comments, or any other text.\n'
            '{\n'
            '  "manufacturer": {"name": "", "street": "", "city": "", "zip": "", "country": "", "email": "", "phone": "", "website": ""},\n'
            '  "eu_responsible": {"name": "", "street": "", "city": "", "zip": "", "country": "", "email": "", "phone": "", "website": ""},\n'
            '  "ce_compliance": "CE compliance / EU declaration of conformity details",\n'
            '  "safety_record": "Safety information, hazards and warnings"\n'
            '}\n'
            'Rules:\n'
            '- "manufacturer" is the product manufacturer (a company).\n'
            '- "eu_responsible" is the EU Responsible Person under GPSR.\n'
            '- "country" should be the country name or ISO code.\n'
            '- Do NOT include any of our own existing contacts or partner data; only research public information.\n'
            'Product information:\n%(context)s'
        ) % {'context': context_text}
        provider = agent._get_provider()
        service = LLMApiService(self.env, provider=provider)
        response = service.request_llm(
            agent.llm_model,
            [agent.system_prompt or 'You are a careful GPSR compliance research agent.'],
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

    def _apply_result(self, result):
        manufacturer = result.get('manufacturer') or {}
        eu_responsible = result.get('eu_responsible') or {}
        self.m_name = (manufacturer.get('name') or '').strip() or False
        self.m_street = (manufacturer.get('street') or '').strip() or False
        self.m_city = (manufacturer.get('city') or '').strip() or False
        self.m_zip = (manufacturer.get('zip') or '').strip() or False
        self.m_country_id = self._resolve_country(manufacturer.get('country')).id
        self.m_email = (manufacturer.get('email') or '').strip() or False
        self.m_phone = (manufacturer.get('phone') or '').strip() or False
        self.m_website = (manufacturer.get('website') or '').strip() or False

        self.r_name = (eu_responsible.get('name') or '').strip() or False
        self.r_street = (eu_responsible.get('street') or '').strip() or False
        self.r_city = (eu_responsible.get('city') or '').strip() or False
        self.r_zip = (eu_responsible.get('zip') or '').strip() or False
        self.r_country_id = self._resolve_country(eu_responsible.get('country')).id
        self.r_email = (eu_responsible.get('email') or '').strip() or False
        self.r_phone = (eu_responsible.get('phone') or '').strip() or False
        self.r_website = (eu_responsible.get('website') or '').strip() or False

        self.ce_compliance = (result.get('ce_compliance') or '').strip() or False
        self.safety_record = (result.get('safety_record') or '').strip() or False

        self._recommend_contact('manufacturer')
        self._recommend_contact('eu_responsible')
        self.same_company_note = (
            _('Manufacturer and EU Responsible Person appear to be the same company (common for EU '
              'companies). They will be linked to a single contact.')
            if self._proposals_are_same() else False
        )

    def _recommend_contact(self, role):
        name = self['%s_name' % ('m' if role == 'manufacturer' else 'r')]
        email = self['%s_email' % ('m' if role == 'manufacturer' else 'r')]
        website = self['%s_website' % ('m' if role == 'manufacturer' else 'r')]
        candidates = self._find_similar(name, email, website)
        candidate_field = '%s_candidate_ids' % ('manufacturer' if role == 'manufacturer' else 'eu_responsible')
        use_field = '%s_use_partner_id' % ('manufacturer' if role == 'manufacturer' else 'eu_responsible')
        action_field = '%s_action' % ('manufacturer' if role == 'manufacturer' else 'eu_responsible')
        note_field = '%s_note' % ('manufacturer' if role == 'manufacturer' else 'eu_responsible')
        self[candidate_field] = [fields.Command.set(candidates.ids)]
        if candidates:
            self[use_field] = candidates[:1]
            self[action_field] = 'use_existing'
            self[note_field] = _(
                'Found %(count)s similar existing contact(s). Recommended: %(name)s. '
                'Review the suggestion or choose to create a new contact instead.'
            ) % {'count': len(candidates), 'name': candidates[:1].display_name}
        else:
            self[use_field] = False
            self[action_field] = 'create'
            self[note_field] = _(
                'No similar existing contact found. A new contact will be created unless you skip.'
            )

    def _find_similar(self, name, email, website):
        conditions = []
        if name:
            conditions.append(('name', 'ilike', name))
        if email:
            conditions.append(('email', 'ilike', email))
        if website:
            conditions.append(('website', 'ilike', website))
        if not conditions:
            return self.env['res.partner']
        domain = ['|'] * (len(conditions) - 1) + conditions
        partners = self.env['res.partner'].search(domain, limit=10)
        if name:
            exact = partners.filtered(lambda p: p.name and p.name.lower() == name.lower())
            if exact:
                partners = exact + partners.filtered(lambda p: p not in exact)
        return partners

    def _resolve_country(self, value):
        if not value:
            return self.env['res.country']
        country = self.env['res.country'].search([('name', 'ilike', value)], limit=1)
        if not country:
            country = self.env['res.country'].search([('code', '=ilike', value)], limit=1)
        return country

    def action_apply(self):
        self.ensure_one()
        product = self.resale_product_id
        vals = {}
        if self.ce_compliance:
            vals['ce_compliance'] = self.ce_compliance
        if self.safety_record:
            vals['safety_record'] = self.safety_record

        manufacturer, manufacturer_new = self._resolve_contact('manufacturer')
        eu_responsible, eu_responsible_new = self._resolve_contact('eu_responsible')

        if self._proposals_are_same() and manufacturer and eu_responsible and manufacturer != eu_responsible:
            if eu_responsible_new:
                eu_responsible.unlink()
                eu_responsible = manufacturer
            elif manufacturer_new:
                manufacturer.unlink()
                manufacturer = eu_responsible

        if manufacturer:
            vals['manufacturer_id'] = manufacturer.id
        if eu_responsible:
            vals['eu_responsible_person_id'] = eu_responsible.id

        product.write(vals)
        self.state = 'done'
        return {'type': 'ir.actions.act_window_close'}

    def _resolve_contact(self, role):
        prefix = 'm' if role == 'manufacturer' else 'r'
        action = self['%s_action' % role]
        if action == 'skip':
            return self.env['res.partner'], False
        if action == 'use_existing':
            return self['%s_use_partner_id' % role], False
        name = self['%s_name' % prefix]
        if not name:
            return self.env['res.partner'], False
        partner = self.env['res.partner'].create({
            'name': name,
            'is_company': True,
            'street': self['%s_street' % prefix],
            'city': self['%s_city' % prefix],
            'zip': self['%s_zip' % prefix],
            'country_id': self['%s_country_id' % prefix].id,
            'email': self['%s_email' % prefix],
            'phone': self['%s_phone' % prefix],
            'website': self['%s_website' % prefix],
        })
        return partner, True

    def _proposals_are_same(self):
        m_name = (self.m_name or '').strip().lower()
        r_name = (self.r_name or '').strip().lower()
        if m_name and r_name and m_name == r_name:
            return True
        m_web = (self.m_website or '').strip().lower()
        r_web = (self.r_website or '').strip().lower()
        m_mail = (self.m_email or '').strip().lower()
        r_mail = (self.r_email or '').strip().lower()
        if (m_web and m_web == r_web) or (m_mail and m_mail == r_mail):
            return True
        return False

    def _reload(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
