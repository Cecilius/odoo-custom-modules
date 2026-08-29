from odoo.tests.common import TransactionCase


class TestResaleAIProductWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env['product.category'].create({
            'name': 'Test AI Category',
            'category_code': '99',
        })

    def _create_wizard(self, **vals):
        defaults = {
            'result_name': 'Test Product AI',
            'result_ean': '1234567890128',
            'result_category_id': self.category.id,
        }
        defaults.update(vals)
        return self.env['resale.product.wizard'].create(defaults)

    def test_create_product_with_template(self):
        wizard = self._create_wizard(from_template=True)
        action = wizard.action_create_product()
        resale = self.env['resale.product'].search([('name', '=', 'Test Product AI')])
        self.assertEqual(len(resale), 1)
        self.assertEqual(len(resale.product_template_ids), 1)
        self.assertEqual(action['res_model'], 'product.template')

    def test_create_product_without_template(self):
        wizard = self._create_wizard(from_template=False)
        action = wizard.action_create_product()
        resale = self.env['resale.product'].search([('name', '=', 'Test Product AI')])
        self.assertEqual(len(resale), 1)
        self.assertEqual(len(resale.product_template_ids), 0)
        self.assertEqual(action['res_model'], 'resale.product')

    def test_matched_flow_creates_template_when_enabled(self):
        resale = self.env['resale.product'].create({
            'name': 'Existing Product', 'ean': '5555555555550'})
        wizard = self.env['resale.product.wizard'].create({
            'ean': '5555555555550', 'from_template': True})
        wizard.action_research()
        wizard = self.env['resale.product.wizard'].browse(wizard.id)
        self.assertEqual(wizard.state, 'matched')
        self.assertEqual(wizard.match_existing_product_id, resale)
        action = wizard.action_open_existing()
        self.assertEqual(len(resale.product_template_ids), 1)
        self.assertEqual(action['res_model'], 'product.template')

    def test_matched_flow_no_template_when_disabled(self):
        resale = self.env['resale.product'].create({
            'name': 'Existing Product Two', 'ean': '6666666666666'})
        wizard = self.env['resale.product.wizard'].create({
            'ean': '6666666666666', 'from_template': False})
        wizard.action_research()
        wizard = self.env['resale.product.wizard'].browse(wizard.id)
        self.assertEqual(wizard.state, 'matched')
        action = wizard.action_open_existing()
        self.assertEqual(len(resale.product_template_ids), 0)
        self.assertEqual(action['res_model'], 'resale.product')

    def test_matched_flow_creates_new_template_when_one_exists(self):
        resale = self.env['resale.product'].create({
            'name': 'Existing Product Three', 'ean': '2111111111115'})
        old_template = self.env['product.template'].create({
            'name': 'Linked Template', 'resale_product_id': resale.id})
        wizard = self.env['resale.product.wizard'].create({
            'ean': '2111111111115', 'from_template': True})
        wizard.action_research()
        wizard = self.env['resale.product.wizard'].browse(wizard.id)
        self.assertEqual(wizard.state, 'matched')
        action = wizard.action_open_existing()
        self.assertEqual(action['res_model'], 'product.template')
        new_template = self.env['product.template'].browse(action['res_id'])
        self.assertNotEqual(new_template.id, old_template.id)
        self.assertIn(new_template, resale.product_template_ids)
        self.assertEqual(len(resale.product_template_ids), 2)
