#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import unittest
from unittest.mock import patch, mock_open, call
import os
import sys
import yaml
import json

# Add the wrenchai directory to the sys.path to allow importing modules
sys.path.insert(0, '.')

from core.playbook_discovery import PlaybookManager, get_playbook_manager

# Sample playbook content
PLAYBOOK_CONTENT_SIMPLE = """
steps:
  - step_id: step1
    tool: tool1
    parameters:
      input: value1
"""

PLAYBOOK_CONTENT_WITH_METADATA = """
- step_id: metadata
  metadata:
    name: my-test-playbook-meta
    description: A test playbook with metadata
    parameters:
      param1:
        type: string
        required: true
- step_id: step1
  tool: tool1
"""

PLAYBOOK_CONTENT_WITH_PARAMS_DICT = """
id: my-test-playbook-params-dict
title: Playbook with Params Dict
description: Describes params from a dict
parameters:
  paramA:
    type: integer
    default: 10
  paramB:
    type: boolean
steps:
  - step_id: step1
    tool: tool1
"""

class TestPlaybookDiscovery(unittest.TestCase):

    @patch('core.playbook_discovery.os.path.exists')
    @patch('core.playbook_discovery.os.listdir')
    @patch('core.playbook_discovery.PlaybookManager._load_playbook_file')
    def test_load_all_playbooks_from_dirs(self, mock_load_playbook_file, mock_listdir, mock_exists):
        mock_exists.return_value = True
        mock_listdir.return_value = ['playbook1.yaml', 'playbook2.yml', 'other_file.txt']
        
        # Mock the return values of _load_playbook_file
        mock_load_playbook_file.side_effect = [
            {'id': 'playbook1', 'title': 'Playbook One', 'description': 'Desc 1'},
            {'id': 'playbook2', 'title': 'Playbook Two', 'description': 'Desc 2'}
        ]

        manager = PlaybookManager(playbook_dirs=['/fake/dir1'])
        
        mock_exists.assert_called_once_with('/fake/dir1')
        mock_listdir.assert_called_once_with('/fake/dir1')
        self.assertEqual(mock_load_playbook_file.call_count, 2) # Called for both .yaml and .yml
        mock_load_playbook_file.assert_has_calls([
            call('/fake/dir1/playbook1.yaml'),
            call('/fake/dir1/playbook2.yml')
        ], any_order=True)

        self.assertIn('playbook1', manager.playbooks)
        self.assertIn('playbook2', manager.playbooks)
        self.assertEqual(len(manager.playbooks), 2)
    
    @patch('core.playbook_discovery.os.path.exists')
    @patch('core.playbook_discovery.os.listdir')
    @patch('core.playbook_discovery.PlaybookManager._load_playbook_file')
    def test_load_all_playbooks_no_dirs_exist(self, mock_load_playbook_file, mock_listdir, mock_exists):
        mock_exists.return_value = False
        
        manager = PlaybookManager(playbook_dirs=['/fake/dir1', '/fake/dir2'])
        
        self.assertEqual(mock_exists.call_count, 2) # Called for both dirs
        mock_exists.assert_has_calls([call('/fake/dir1'), call('/fake/dir2')], any_order=True)
        mock_listdir.assert_not_called()
        mock_load_playbook_file.assert_not_called()
        self.assertEqual(len(manager.playbooks), 0)

    @patch('core.playbook_discovery.yaml.safe_load')
    @patch('core.playbook_discovery.open', new_callable=mock_open)
    @patch('core.playbook_discovery.os.path.basename')
    @patch('core.playbook_discovery.os.path.splitext')
    def test_load_playbook_file_simple(self, mock_splitext, mock_basename, mock_file_open, mock_yaml_load):
        mock_basename.return_value = 'simple_playbook.yaml'
        mock_splitext.return_value = ('simple_playbook', '.yaml')
        mock_yaml_load.return_value = yaml.safe_load(PLAYBOOK_CONTENT_SIMPLE) # Load actual content

        manager = PlaybookManager([]) # Initialize with empty dirs to avoid loading
        playbook = manager._load_playbook_file('/fake/dir/simple_playbook.yaml')

        mock_file_open.assert_called_once_with('/fake/dir/simple_playbook.yaml', 'r')
        mock_yaml_load.assert_called_once_with(mock_file_open())
        self.assertEqual(playbook['id'], 'simple_playbook')
        self.assertEqual(playbook['title'], 'Simple Playbook')
        self.assertEqual(playbook['description'], 'No description')
        self.assertIn('steps', playbook)
        self.assertEqual(playbook['source_path'], '/fake/dir/simple_playbook.yaml')

    @patch('core.playbook_discovery.yaml.safe_load')
    @patch('core.playbook_discovery.open', new_callable=mock_open)
    @patch('core.playbook_discovery.os.path.basename') # Should not be called
    @patch('core.playbook_discovery.os.path.splitext') # Should not be called
    def test_load_playbook_file_with_metadata(self, mock_splitext, mock_basename, mock_file_open, mock_yaml_load):
        mock_yaml_load.return_value = yaml.safe_load(PLAYBOOK_CONTENT_WITH_METADATA)

        manager = PlaybookManager([])
        playbook = manager._load_playbook_file('/fake/dir/meta_playbook.yaml')

        mock_file_open.assert_called_once_with('/fake/dir/meta_playbook.yaml', 'r')
        mock_yaml_load.assert_called_once_with(mock_file_open())
        mock_basename.assert_not_called()
        mock_splitext.assert_not_called()

        self.assertEqual(playbook['id'], 'my-test-playbook-meta')
        self.assertEqual(playbook['title'], 'A test playbook with metadata') # Title should come from description in metadata
        self.assertEqual(playbook['description'], 'A test playbook with metadata')
        self.assertIn('steps', playbook)
        self.assertEqual(playbook['source_path'], '/fake/dir/meta_playbook.yaml')
        self.assertIn({'step_id': 'step1', 'tool': 'tool1'}, playbook['steps'])

    def test_get_playbook(self):
        manager = PlaybookManager([])
        manager.playbooks = {
            'pb1': {'id': 'pb1', 'title': 'PB 1'},
            'pb2': {'id': 'pb2', 'title': 'PB 2'}
        }

        playbook = manager.get_playbook('pb1')
        self.assertEqual(playbook, {'id': 'pb1', 'title': 'PB 1'})

        playbook_not_found = manager.get_playbook('pb3')
        self.assertIsNone(playbook_not_found)

    def test_get_all_playbooks(self):
        manager = PlaybookManager([])
        manager.playbooks = {
            'pb1': {'id': 'pb1', 'title': 'PB 1'},
            'pb2': {'id': 'pb2', 'title': 'PB 2'}
        }
        all_playbooks = manager.get_all_playbooks()
        self.assertEqual(len(all_playbooks), 2)
        self.assertIn({'id': 'pb1', 'title': 'PB 1'}, all_playbooks)
        self.assertIn({'id': 'pb2', 'title': 'PB 2'}, all_playbooks)

    def test_get_playbook_summary(self):
        manager = PlaybookManager([])
        manager.playbooks = {
            'pb1': {'id': 'pb1', 'title': 'PB 1', 'description': 'Desc 1'},
            'pb2': {'id': 'pb2', 'title': 'PB 2', 'description': 'Desc 2'}
        }
        summary = manager.get_playbook_summary()
        self.assertEqual(len(summary), 2)
        self.assertIn({'id': 'pb1', 'title': 'PB 1', 'description': 'Desc 1'}, summary)
        self.assertIn({'id': 'pb2', 'title': 'PB 2', 'description': 'Desc 2'}, summary)
        
    def test_get_playbook_summary_missing_fields(self):
        manager = PlaybookManager([])
        manager.playbooks = {
            'pb1': {'id': 'pb1'},
            'pb2': {'id': 'pb2', 'title': 'PB 2'}
        }
        summary = manager.get_playbook_summary()
        self.assertEqual(len(summary), 2)
        self.assertIn({'id': 'pb1', 'title': 'Unnamed', 'description': 'No description'}, summary)
        self.assertIn({'id': 'pb2', 'title': 'PB 2', 'description': 'No description'}, summary)

    def test_get_playbook_parameters_list(self):
        manager = PlaybookManager([])
        manager.playbooks = {
            'pb_params_list': {
                'id': 'pb_params_list',
                'parameters': [
                    {'name': 'paramA', 'type': 'string'},
                    {'name': 'paramB', 'type': 'integer', 'required': True}
                ],
                'steps': []
            }
        }
        params = manager.get_playbook_parameters('pb_params_list')
        self.assertEqual(len(params), 2)
        self.assertIn({'name': 'paramA', 'type': 'string'}, params)
        self.assertIn({'name': 'paramB', 'type': 'integer', 'required': True}, params)
        
    @patch('core.playbook_discovery.yaml.safe_load')
    @patch('core.playbook_discovery.open', new_callable=mock_open)
    @patch('core.playbook_discovery.os.path.basename')
    @patch('core.playbook_discovery.os.path.splitext')
    def test_load_playbook_file_with_params_dict(self, mock_splitext, mock_basename, mock_file_open, mock_yaml_load):
        mock_basename.return_value = 'params_dict_playbook.yaml'
        mock_splitext.return_value = ('params_dict_playbook', '.yaml')
        mock_yaml_load.return_value = yaml.safe_load(PLAYBOOK_CONTENT_WITH_PARAMS_DICT)

        manager = PlaybookManager([])
        playbook = manager._load_playbook_file('/fake/dir/params_dict_playbook.yaml')
        
        self.assertIn('parameters', playbook)
        params = playbook['parameters']
        #self.assertIsInstance(params, dict) # Should still be a dict after loading
        self.assertIn('paramA', params)
        self.assertIn('paramB', params)

    def test_get_playbook_parameters_dict(self):
        manager = PlaybookManager([])
        manager.playbooks = {
            'pb_params_dict': yaml.safe_load(PLAYBOOK_CONTENT_WITH_PARAMS_DICT)
        }
        params = manager.get_playbook_parameters('pb_params_dict')
        self.assertEqual(len(params), 2)
        # The manager should convert the dict to the list format for get_playbook_parameters
        self.assertIn({'name': 'paramA', 'type': 'integer', 'default': 10}, params)
        self.assertIn({'name': 'paramB', 'type': 'boolean'}, params) # Required defaults to False

    def test_get_playbook_parameters_no_params(self):
        manager = PlaybookManager([])
        manager.playbooks = {
            'pb_no_params': {
                'id': 'pb_no_params',
                'steps': []
            }
        }
        params = manager.get_playbook_parameters('pb_no_params')
        self.assertEqual(len(params), 0)
        self.assertEqual(params, [])

    def test_get_playbook_parameters_playbook_not_found(self):
        manager = PlaybookManager([])
        params = manager.get_playbook_parameters('nonexistent-playbook')
        self.assertEqual(len(params), 0)
        self.assertEqual(params, [])

if __name__ == '__main__':
    unittest.main()
