"""Configurable outcomes used by operator product tests."""

from odoo import fields, models


class ResaleProductTestResult(models.Model):
    """A named, ordered, and optionally archived test outcome."""
    _name = 'resale.product.test.result'
    _description = 'Resale Product Test Result'
    _order = 'sequence, name, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _result_name_unique = models.Constraint(
        'unique(name)',
        'Each product test result must have a unique name.',
    )
