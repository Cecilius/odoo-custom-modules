#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parents[1]
odoo_root = repo_root / 'odoo-enterprise'
sys.path.insert(0, str(odoo_root))
sys.path.insert(0, str(odoo_root / 'odoo'))

import odoo
from odoo import api
from odoo.tools.config import parse_config


def get_env(db_name, config_file=None):
    args = ['odoo-bin']
    if config_file:
        args += ['-c', config_file]
    parse_config(args)
    registry = odoo.registry(db_name)
    return registry


def verify_module(registry):
    with registry.cursor() as cr:
        env = api.Environment(cr, odoo.SUPERUSER_ID, {})
        print('> Verifying repair_helpdesk module installation...')
        module = env['ir.module.module'].search([
            ('name', '=', 'repair_helpdesk'),
            ('state', '=', 'installed'),
        ], limit=1)
        print('  repair_helpdesk installed:', bool(module))

        print('\n> Verifying quality dependency...')
        quality_points = env['quality.point'].search([('name', 'ilike', 'Incoming Inspection -')])
        print('  Found quality inspection points:', len(quality_points))
        for point in quality_points:
            print('   -', point.name)

        print('\n> Verifying repair locations...')
        location_names = [
            'Repair Workshop',
            'Incoming Inspection Location',
            'Awaiting Repair Location',
            'Repair In Progress Location',
            'Quality Control / Awaiting Shipment',
            'Repair Return Dispatch',
        ]
        for name in location_names:
            location = env['stock.location'].search([('name', '=', name)], limit=1)
            print(f'  {name}:', bool(location))

        print('\n> Verifying stock routes...')
        routes = env['stock.route'].search([('name', 'ilike', 'Repair')])
        print('  Found repair routes:', len(routes))
        for route in routes:
            print('   -', route.name, '| rules:', len(route.rule_ids))

        print('\n> Verifying quality check hook support...')
        picking_model = env['ir.model.fields'].search([
            ('model', '=', 'stock.picking'),
            ('name', '=', 'helpdesk_ticket_id'),
        ], limit=1)
        print('  stock.picking.helpdesk_ticket_id field exists:', bool(picking_model))

        check_model = env['ir.model.fields'].search([
            ('model', '=', 'quality.check'),
            ('name', '=', 'picking_id'),
        ], limit=1)
        print('  quality.check.picking_id field exists:', bool(check_model))

        print('\nDone. If all checks are true, the repair helpdesk integration is installed correctly.')


def main():
    parser = argparse.ArgumentParser(description='Verify repair_helpdesk integration in Odoo.')
    parser.add_argument('-d', '--database', required=True, help='Odoo database name')
    parser.add_argument('-c', '--config', help='Path to Odoo configuration file')
    args = parser.parse_args()

    registry = get_env(args.database, args.config)
    verify_module(registry)


if __name__ == '__main__':
    main()
