#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import unittest
from unittest.mock import patch
import sys

# Add the wrenchai directory to the sys.path to allow importing modules
sys.path.insert(0, '.')

from wai_cli import WrenchAICliApp

class TestCliArguments(unittest.TestCase):

    def setUp(self):
        # Create a new instance of the app for each test
        self.app = WrenchAICliApp()

    def test_list_command_default_format(self):
        args = self.app.parser.parse_args(['list'])
        self.assertEqual(args.command, 'list')
        self.assertEqual(args.format, 'table')

    def test_list_command_json_format(self):
        args = self.app.parser.parse_args(['list', '--format', 'json'])
        self.assertEqual(args.command, 'list')
        self.assertEqual(args.format, 'json')

    def test_select_command_default_format(self):
        args = self.app.parser.parse_args(['select', 'my-playbook-id'])
        self.assertEqual(args.command, 'select')
        self.assertEqual(args.id, 'my-playbook-id')
        self.assertEqual(args.format, 'yaml')

    def test_select_command_json_format(self):
        args = self.app.parser.parse_args(['select', 'my-playbook-id', '--format', 'json'])
        self.assertEqual(args.command, 'select')
        self.assertEqual(args.id, 'my-playbook-id')
        self.assertEqual(args.format, 'json')

    def test_describe_command_default_format(self):
        args = self.app.parser.parse_args(['describe', 'my-playbook-id'])
        self.assertEqual(args.command, 'describe')
        self.assertEqual(args.id, 'my-playbook-id')
        self.assertEqual(args.format, 'table')

    def test_describe_command_yaml_format(self):
        args = self.app.parser.parse_args(['describe', 'my-playbook-id', '--format', 'yaml'])
        self.assertEqual(args.command, 'describe')
        self.assertEqual(args.id, 'my-playbook-id')
        self.assertEqual(args.format, 'yaml')
        
    def test_run_command_minimum_args(self):
        args = self.app.parser.parse_args(['run', 'my-playbook-id'])
        self.assertEqual(args.command, 'run')
        self.assertEqual(args.id, 'my-playbook-id')
        self.assertFalse(args.verbose)
        self.assertIsNone(args.params)
        self.assertIsNone(args.model)
        self.assertIsNone(args.mcp_config)
        self.assertIsNone(args.log_file)

    def test_run_command_all_args(self):
        args = self.app.parser.parse_args([
            '--verbose',
            'run', 'another-playbook-id', 
            '--param', 'name1=value1', 
            '--param', 'name2=value2',
            '--model', 'gpt-4',
            '--mcp-config', './mcp.json',
            '--log-file', '/tmp/log.txt'
        ])
        self.assertEqual(args.command, 'run')
        self.assertEqual(args.id, 'another-playbook-id')
        self.assertTrue(args.verbose)
        self.assertEqual(args.params, ['name1=value1', 'name2=value2'])
        self.assertEqual(args.model, 'gpt-4')
        self.assertEqual(args.mcp_config, './mcp.json')
        self.assertEqual(args.log_file, '/tmp/log.txt')

if __name__ == '__main__':
    unittest.main()
