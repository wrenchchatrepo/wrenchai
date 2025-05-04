#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json
import yaml
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wai_cli import WrenchAICliApp

class TestWrenchAICli(unittest.TestCase):
    """Tests for the WrenchAI CLI"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = WrenchAICliApp()
        
        # Mock the playbook manager
        self.playbooks_patch = patch('core.playbook_discovery.get_playbook_manager')
        self.mock_get_manager = self.playbooks_patch.start()
        
        # Create a mock playbook manager
        self.mock_manager = MagicMock()
        self.mock_get_manager.return_value = self.mock_manager
        
        # Set up example playbooks
        self.example_playbooks = [
            {
                "id": "example",
                "title": "Example Playbook",
                "description": "A simple example playbook"
            },
            {
                "id": "code-review",
                "title": "Code Review",
                "description": "Review code for best practices"
            }
        ]
        
        # Configure the mock manager
        self.mock_manager.get_playbook_summary.return_value = self.example_playbooks
        self.mock_manager.get_playbook.return_value = {
            "id": "example",
            "title": "Example Playbook",
            "description": "A simple example playbook",
            "parameters": [
                {
                    "name": "project_name",
                    "type": "string",
                    "description": "Name of the project",
                    "required": True
                },
                {
                    "name": "language",
                    "type": "string",
                    "description": "Programming language to use",
                    "required": True,
                    "default": "python"
                }
            ]
        }
        self.mock_manager.get_playbook_parameters.return_value = [
            {
                "name": "project_name",
                "type": "string",
                "description": "Name of the project",
                "required": True
            },
            {
                "name": "language",
                "type": "string",
                "description": "Programming language to use",
                "required": True,
                "default": "python"
            }
        ]
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.playbooks_patch.stop()
    
    def test_list_command(self):
        """Test the 'list' command"""
        # Redirect stdout to capture output
        stdout_backup = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            # Execute the command
            result = self.app.run(["list", "--format", "json"])
            
            # Get the captured output
            output = sys.stdout.getvalue()
            
            # Check the result
            self.assertEqual(result, 0)
            
            # Check that the playbook manager was called
            self.mock_manager.get_playbook_summary.assert_called_once()
            
            # Parse the JSON output
            playbooks = json.loads(output)
            
            # Check the output
            self.assertEqual(len(playbooks), 2)
            self.assertEqual(playbooks[0]["id"], "example")
            self.assertEqual(playbooks[1]["id"], "code-review")
        finally:
            # Restore stdout
            sys.stdout = stdout_backup
    
    def test_select_command(self):
        """Test the 'select' command"""
        # Redirect stdout to capture output
        stdout_backup = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            # Execute the command
            result = self.app.run(["select", "example", "--format", "json"])
            
            # Get the captured output
            output = sys.stdout.getvalue()
            
            # Check the result
            self.assertEqual(result, 0)
            
            # Check that the playbook manager was called
            self.mock_manager.get_playbook.assert_called_once_with("example")
            
            # Parse the JSON output
            playbook = json.loads(output)
            
            # Check the output
            self.assertEqual(playbook["id"], "example")
            self.assertEqual(playbook["title"], "Example Playbook")
        finally:
            # Restore stdout
            sys.stdout = stdout_backup
    
    def test_describe_command(self):
        """Test the 'describe' command"""
        # Redirect stdout to capture output
        stdout_backup = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            # Execute the command
            result = self.app.run(["describe", "example", "--format", "json"])
            
            # Get the captured output
            output = sys.stdout.getvalue()
            
            # Check the result
            self.assertEqual(result, 0)
            
            # Check that the playbook manager was called
            self.mock_manager.get_playbook.assert_called_once_with("example")
            self.mock_manager.get_playbook_parameters.assert_called_once_with("example")
            
            # Parse the JSON output
            params = json.loads(output)
            
            # Check the output
            self.assertEqual(len(params), 2)
            self.assertEqual(params[0]["name"], "project_name")
            self.assertEqual(params[1]["name"], "language")
        finally:
            # Restore stdout
            sys.stdout = stdout_backup

if __name__ == "__main__":
    unittest.main()