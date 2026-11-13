from odoo.tests.common import TransactionCase, new_test_user


class TestResaleGroups(TransactionCase):
    def test_internal_user_gets_resale_user_only(self):
        user = new_test_user(self.env, login='resale_plain_user', groups='base.group_user')
        self.assertTrue(user.has_group('resale_base.group_resale_user'))
        self.assertFalse(user.has_group('resale_base.group_resale_manager'))

    def test_settings_administrator_is_resale_manager(self):
        admin = new_test_user(self.env, login='resale_admin_user', groups='base.group_system')
        self.assertTrue(admin.has_group('resale_base.group_resale_manager'))

    def test_portal_user_has_no_resale_access(self):
        portal = new_test_user(self.env, login='resale_portal_user', groups='base.group_portal')
        self.assertFalse(portal.has_group('resale_base.group_resale_user'))
