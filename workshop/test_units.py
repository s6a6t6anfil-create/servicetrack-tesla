"""Isolated function tests: no database, HTTP server or browser required."""
from types import SimpleNamespace
from unittest.mock import Mock
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from .views import parse_identifier
from .services import is_manager
from .serializers import OrderSerializer


class IdentifierUnitTests(SimpleTestCase):
    def test_valid_boundaries_and_leading_zeroes(self):
        # Arrange: query parameters are strings, including the SQLite upper bound.
        cases = [('0', 0), ('00042', 42), ('9223372036854775807', 9223372036854775807)]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                actual = parse_identifier(raw, 'vehicle')  # Act
                self.assertEqual(actual, expected)  # Assert

    def test_rejects_non_decimal_and_unicode_lookalikes(self):
        for raw in ['', '-1', '+1', '1.5', '1e3', ' 1', '1 ', '²', '１２', '١٢', 'abc']:
            with self.subTest(raw=raw):
                with self.assertRaises(ValidationError) as error:
                    parse_identifier(raw, 'customer')
                self.assertIn('customer', error.exception.detail)

    def test_rejects_overflow_and_excessive_length(self):
        for raw in ['9223372036854775808', '9' * 100, '0' * 20]:
            with self.subTest(raw=raw):
                with self.assertRaises(ValidationError):
                    parse_identifier(raw, 'number')


class ManagerUnitTests(SimpleTestCase):
    def test_superuser_does_not_need_group_lookup(self):
        user = SimpleNamespace(is_superuser=True, groups=Mock())
        result = is_manager(user)
        self.assertTrue(result)
        user.groups.filter.assert_not_called()

    def test_administrator_group_grants_access(self):
        groups = Mock()
        groups.filter.return_value.exists.return_value = True
        user = SimpleNamespace(is_superuser=False, groups=groups)
        self.assertTrue(is_manager(user))
        groups.filter.assert_called_once_with(name='Адміністратор')

    def test_missing_administrator_group_denies_access(self):
        groups = Mock()
        groups.filter.return_value.exists.return_value = False
        self.assertFalse(is_manager(SimpleNamespace(is_superuser=False, groups=groups)))


class MechanicUnitTests(SimpleTestCase):
    def test_unassigned_is_valid(self):
        self.assertIsNone(OrderSerializer().validate_mechanic(None))

    def test_active_mechanic_is_returned_unchanged(self):
        groups = Mock()
        groups.filter.return_value.exists.return_value = True
        user = SimpleNamespace(is_active=True, groups=groups)
        self.assertIs(OrderSerializer().validate_mechanic(user), user)
        groups.filter.assert_called_once_with(name='Механік')

    def test_inactive_or_wrong_role_is_rejected(self):
        for active, member in [(False, True), (True, False), (False, False)]:
            with self.subTest(active=active, member=member):
                groups = Mock()
                groups.filter.return_value.exists.return_value = member
                user = SimpleNamespace(is_active=active, groups=groups)
                with self.assertRaises(ValidationError):
                    OrderSerializer().validate_mechanic(user)
                if not active:
                    groups.filter.assert_not_called()
