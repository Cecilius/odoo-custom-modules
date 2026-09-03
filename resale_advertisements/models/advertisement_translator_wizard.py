"""Wizard for translating product descriptions while preserving HTML blocks."""

import json
import re

from odoo import _, api, fields, models
from odoo.addons.resale_ai_base.models.ai_service import ResaleAIRequestError
from odoo.exceptions import UserError
from odoo.tools.mail import html2plaintext


class ResaleAdvertisementTranslator(models.TransientModel):
    """Translate one listing and map each returned block to its source term."""
    _name = 'resale.advertisement.translator'
    _description = 'AI Description Translator'

    product_template_id = fields.Many2one(
        'product.template', required=True, ondelete='cascade',
    )
    source_lang = fields.Char(string='Source language', readonly=True)
    target_lang_id = fields.Many2one(
        'res.lang', string='Target language', required=True,
        domain="[('active', '=', True), ('code', '!=', source_lang)]",
    )
    source_text = fields.Text(string='Source listing (plain text)', readonly=True)
    translated_text = fields.Text(string='Translated listing', readonly=True)
    translated_terms = fields.Text(string='Translated terms (JSON)', readonly=True)
    error_message = fields.Text(string='Status', readonly=True)
    state = fields.Selection(
        [('draft', 'Ready'), ('confirm_overwrite', 'Confirm Overwrite'),
         ('done', 'Done'), ('error', 'Error')],
        default='draft', required=True,
    )

    @api.model
    def default_get(self, fields_list):
        """Prepare source language, target language, and plain-text source content."""
        vals = super().default_get(fields_list)
        product = self.env['product.template'].browse(
            self.env.context.get('default_product_template_id')
        )
        if not product:
            raise UserError(_('No product selected for translation.'))
        current_lang = self.env.context.get('lang') or self.env.user.lang or 'en_US'
        other_langs = self.env['res.lang'].search([
            ('active', '=', True), ('code', '!=', current_lang),
        ])
        if not other_langs:
            raise UserError(_(
                'No other language is installed. Install and activate another '
                'language before translating the listing.'
            ))
        if not product.description_ecommerce:
            raise UserError(_(
                'The description is empty. Write or generate a description in the '
                'current language before translating it.'
            ))
        vals['product_template_id'] = product.id
        vals['source_lang'] = current_lang
        vals['target_lang_id'] = other_langs[0].id
        vals['source_text'] = html2plaintext(product.description_ecommerce or '')
        return vals

    def _get_agent(self, key):
        return self.env['resale.ai.service'].get_agent(key)

    def _translation_exists(self, lang_code):
        """Check whether the target language already has a different translation."""
        source = self.product_template_id.description_ecommerce or ''
        translated = self.product_template_id.with_context(lang=lang_code).description_ecommerce or ''
        return bool(translated) and translated != source

    def action_translate(self):
        """Require overwrite confirmation when the target translation exists."""
        self.ensure_one()
        if not self.target_lang_id:
            raise UserError(_('Select a target language.'))
        if self._translation_exists(self.target_lang_id.code):
            self.state = 'confirm_overwrite'
            self.error_message = _(
                'A translation into %s already exists. Continuing will overwrite it.'
            ) % self.target_lang_id.name
            return self._reload()
        return self._run_translation()

    def action_confirm_translate(self):
        self.ensure_one()
        return self._run_translation()

    def _run_translation(self):
        """Translate all source blocks in one request and preserve their ordering."""
        self.ensure_one()
        field = self.product_template_id._fields['description_ecommerce']
        src_html = self.product_template_id.with_context(lang=self.source_lang).description_ecommerce or ''
        # description_ecommerce is an HTML translatable field: Odoo splits it into
        # one translatable term per block (e.g. each <p> or line). We send all
        # blocks in a single translation call (so the whole description is translated
        # with full context) but ask the AI to return one translation per block, then
        # map each source term to its own translation to preserve the structure.
        source_terms = [
            term for term in field.get_translation_dictionary(src_html, {}).keys()
            if html2plaintext(term).strip()
        ]
        if not source_terms:
            self.state = 'error'
            self.error_message = _('The source description is empty.')
            return self._reload()
        agent = self._get_agent('resale_advertisement.translation_agent_id') or self._get_agent('resale_advertisement.research_agent_id')
        if not agent:
            raise UserError(_('Configure a listing translation/research agent in Settings first.'))

        def _translate_all(ag):
            # Send every block in a single call so the AI translates the whole
            # description with full context, while still returning one translation
            # per block (kept separated) to preserve the source structure.
            return self._ask_translate_agent_blocks(ag, source_parts, self.target_lang_id.name)

        source_parts = [html2plaintext(term).strip() for term in source_terms]

        try:
            translated_parts = _translate_all(agent)
        except ResaleAIRequestError as primary_error:
            backup = self._get_agent('resale_advertisement_backup_agent_id')
            if not backup or backup == agent:
                self.state = 'error'
                self.error_message = _('The translation agent failed: %s') % primary_error
                return self._reload()
            try:
                translated_parts = _translate_all(backup)
            except ResaleAIRequestError as backup_error:
                self.state = 'error'
                self.error_message = _(
                    'Both translation agents failed. Primary: %(primary)s. Backup: %(backup)s.'
                ) % {'primary': primary_error, 'backup': backup_error}
                return self._reload()
            self.error_message = False

        self.translated_terms = json.dumps(translated_parts, ensure_ascii=False)
        self.translated_text = '\n\n'.join(translated_parts)
        self.state = 'done'
        return self._reload()

    def _ask_translate_agent_blocks(self, agent, blocks, target_language_name):
        """Request one translated string for each numbered source block."""
        numbered = '\n'.join('%d. %s' % (i + 1, block) for i, block in enumerate(blocks))
        prompt = _(
            'Target language: %(lang)s\nNumber of blocks: %(count)s\n\n%(blocks)s'
        ) % {'lang': target_language_name, 'count': len(blocks), 'blocks': numbered}
        schema = {
            'type': 'object',
            'properties': {
                'translations': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'minItems': len(blocks),
                    'maxItems': len(blocks),
                },
            },
            'required': ['translations'],
        }
        response = self.env['resale.ai.service'].request_llm(
            agent,
            [agent.system_prompt],
            [prompt],
            schema=schema,
        )
        data = self.env['resale.ai.service'].parse_json_response(response)
        parts = data.get('translations') or []
        return [re.sub(r'^\d+\.\s*', '', str(part).strip()) for part in parts]

    def action_apply(self):
        """Apply translations only if the source structure is unchanged."""
        self.ensure_one()
        if not self.translated_terms:
            raise UserError(_('No translated text to apply.'))
        try:
            translated_parts = json.loads(self.translated_terms)
        except (TypeError, ValueError):
            raise UserError(_('The translated text is corrupted.'))
        field = self.product_template_id._fields['description_ecommerce']
        src_html = self.product_template_id.with_context(lang=self.source_lang).description_ecommerce or ''
        source_terms = [
            term for term in field.get_translation_dictionary(src_html, {}).keys()
            if html2plaintext(term).strip()
        ]
        if len(source_terms) != len(translated_parts):
            raise UserError(_(
                'The source description changed after translation was generated. '
                'Please translate it again.'
            ))
        mapping = {}
        for term, translated in zip(source_terms, translated_parts):
            escaped = translated.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            mapping[term] = escaped.replace('\n', '<br/>')
        self.product_template_id.update_field_translations(
            'description_ecommerce',
            {self.target_lang_id.code: mapping},
            source_lang=self.source_lang,
        )
        return {'type': 'ir.actions.act_window_close'}

    def _reload(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
