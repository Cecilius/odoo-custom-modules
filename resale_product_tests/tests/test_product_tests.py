from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user


class TestResaleProductTests(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env['product.template'].create({'name': 'Tested Product'})
        cls.ok = cls.env.ref('resale_product_tests.result_no_issue')
        cls.broken = cls.env.ref('resale_product_tests.result_not_working')

    def _add_test(self, result, date):
        test = self.env['resale.product.test'].create({
            'product_template_id': self.template.id,
            'result_id': result.id,
        })
        # test_date is readonly in the UI only; backdate it for ordering checks.
        test.test_date = date
        return test

    def test_latest_result_is_exposed_on_template_and_variant(self):
        self._add_test(self.broken, '2026-01-01')
        self._add_test(self.ok, '2026-02-01')
        self.template.invalidate_recordset(['resale_product_test_ids', 'resale_last_test_result_id'])
        self.assertEqual(self.template.resale_last_test_result_id, self.ok)
        self.assertEqual(self.template.product_variant_id.resale_last_test_result_id, self.ok)

    def test_no_tests_means_no_result(self):
        self.assertFalse(self.template.resale_last_test_result_id)
        self.assertFalse(self.template.product_variant_id.resale_last_test_result_id)

    def test_users_record_tests_but_managers_define_results(self):
        user = new_test_user(self.env, login='resale_tester', groups='base.group_user')
        test = self.env['resale.product.test'].with_user(user).create({
            'product_template_id': self.template.id,
            'result_id': self.ok.id,
        })
        self.assertEqual(test.tested_by_id, user)
        with self.assertRaises(AccessError):
            self.env['resale.product.test.result'].with_user(user).create({'name': 'Custom'})
