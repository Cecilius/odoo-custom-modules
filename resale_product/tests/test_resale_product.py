from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user


class TestResaleProduct(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ResaleProduct = cls.env['resale.product']

    def test_identifiers_are_normalized(self):
        product = self.ResaleProduct.create({
            'name': 'Console',
            'ean': ' 4006381333931 ',
            'asin': ' b07xjwd7y8 ',
            'launch_year': ' 2019 ',
        })
        self.assertEqual(product.ean, '4006381333931')
        self.assertEqual(product.asin, 'B07XJWD7Y8')
        self.assertEqual(product.launch_year, '2019')

    def test_blank_identifier_becomes_empty(self):
        product = self.ResaleProduct.create({'name': 'Blank', 'ean': '   '})
        self.assertFalse(product.ean)

    def test_invalid_identifiers_are_rejected(self):
        for values in (
            {'ean': '4006381333932'},  # wrong check digit
            {'ean': '12345'},
            {'upc': '036000291453'},  # wrong check digit
            {'asin': 'TOO-SHORT'},
            {'launch_year': '19'},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self.ResaleProduct.create(dict(values, name='Invalid'))

    def test_valid_upc_is_accepted(self):
        product = self.ResaleProduct.create({'name': 'UPC', 'upc': '036000291452'})
        self.assertEqual(product.upc, '036000291452')

    def test_reference_price_change_is_timestamped(self):
        product = self.ResaleProduct.create({'name': 'Priced', 'reference_retail_price': 100.0})
        self.assertTrue(product.reference_retail_price_updated)
        product.reference_retail_price_updated = '2020-01-01'
        product.reference_retail_price = 120.0
        self.assertNotEqual(str(product.reference_retail_price_updated), '2020-01-01')

    def test_action_create_product_links_template(self):
        category = self.env['product.category'].create({'name': 'Resale Test Category'})
        product = self.ResaleProduct.create({'name': 'Linked', 'category_id': category.id})
        action = product.action_create_product()
        template = self.env['product.template'].browse(action['res_id'])
        self.assertEqual(template.resale_product_id, product)
        self.assertEqual(template.categ_id, category)
        self.assertEqual(template.name, 'Linked')

    def test_only_managers_can_delete(self):
        product = self.ResaleProduct.create({'name': 'Protected'})
        user = new_test_user(self.env, login='resale_product_user', groups='base.group_user')
        with self.assertRaises(AccessError):
            product.with_user(user).unlink()
        manager = new_test_user(
            self.env, login='resale_product_manager',
            groups='base.group_user,resale_base.group_resale_manager',
        )
        product.with_user(manager).unlink()
        self.assertFalse(product.exists())
