from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user


class TestResaleAttributes(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.condition_attribute = cls.env.ref('resale_attributes.product_attribute_condition')
        cls.brand_attribute = cls.env.ref('resale_attributes.product_attribute_brand')
        cls.good = cls.env['product.attribute.value'].create({
            'name': 'Good (test)', 'attribute_id': cls.condition_attribute.id,
        })
        cls.mint = cls.env['product.attribute.value'].create({
            'name': 'Mint (test)', 'attribute_id': cls.condition_attribute.id,
        })
        cls.template = cls.env['product.template'].create({'name': 'Attribute Test Product'})

    def test_value_field_writes_attribute_line(self):
        self.template.condition_value_id = self.good
        line = self.template.attribute_line_ids.filtered(
            lambda item: item.attribute_id == self.condition_attribute
        )
        self.assertEqual(line.value_ids, self.good)
        self.template.condition_value_id = False
        self.assertFalse(self.template.attribute_line_ids.filtered(
            lambda item: item.attribute_id == self.condition_attribute
        ))

    def test_direct_attribute_line_edit_updates_values(self):
        self.template.write({'attribute_line_ids': [Command.create({
            'attribute_id': self.condition_attribute.id,
            'value_ids': [Command.link(self.mint.id)],
        })]})
        self.assertEqual(self.template.condition_value_id, self.mint)

    def test_mapping_created_later_is_picked_up(self):
        self.template.condition_value_id = self.good
        self.assertFalse(self.template.condition_text_id)
        mapping = self.env['resale.condition.text'].create({
            'condition_value_id': self.good.id,
            'listing_text': 'Good condition',
        })
        self.assertEqual(self.template.condition_text_id, mapping)
        self.assertEqual(self.template.condition_listing_text, 'Good condition')

    def test_archived_mapping_is_released(self):
        mapping = self.env['resale.condition.text'].create({'condition_value_id': self.good.id})
        self.template.condition_value_id = self.good
        self.assertEqual(self.template.condition_text_id, mapping)
        mapping.active = False
        self.assertFalse(self.template.condition_text_id)

    def test_resale_product_brand_uses_configured_attribute(self):
        resale_product = self.env['resale.product'].create({'name': 'Brand Test'})
        self.assertEqual(resale_product.brand_attribute_id, self.brand_attribute)

    def test_condition_texts_are_manager_configuration(self):
        user = new_test_user(self.env, login='resale_attr_user', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.env['resale.condition.text'].with_user(user).create({
                'condition_value_id': self.mint.id,
            })
