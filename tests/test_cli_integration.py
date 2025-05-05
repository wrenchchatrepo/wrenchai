#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import unittest
from unittest.mock import patch, MagicMock, AsyncMock, call
import sys
import asyncio
import io

# Add the wrenchai directory to the sys.path to allow importing modules
sys.path.insert(0, '.')

from wai_cli import WrenchAICliApp

# Mock dependencies
mock_playbook = {
    'id': 'test-playbook',
    'title': 'Test Playbook',
    'description': 'A simple test playbook',
    'steps': []
}

mock_playbook_summary = [
    {'id': 'test-playbook', 'title': 'Test Playbook', 'description': 'A simple test playbook'}
]

mock_playbook_parameters = [
    {'name': 'param1', 'type': 'string', 'required': True}
]

class TestCliIntegration(unittest.TestCase):

    def setUp(self):
        self.app = WrenchAICliApp()
        self.app.logger = MagicMock() # Mock logger
        
        # Patch key external dependencies
        self.patcher_pydantic_ai_check = patch.object(self.app, '_check_pydantic_ai', return_value=True).start()
        
        self.patcher_playbook_manager = patch('wai_cli.get_playbook_manager').start()
        self.mock_playbook_manager = MagicMock()
        self.mock_playbook_manager.get_playbook.return_value = mock_playbook
        self.mock_playbook_manager.get_playbook_summary.return_value = mock_playbook_summary
        self.mock_playbook_manager.get_playbook_parameters.return_value = mock_playbook_parameters
        self.patcher_playbook_manager.return_value = self.mock_playbook_manager

        self.patcher_super_agent = patch('wai_cli.SuperAgent').start()
        self.mock_super_agent_instance = MagicMock()
        # Configure execute_playbook to return a successful result by default
        self.mock_super_agent_instance.execute_playbook = AsyncMock(
            return_value={'result': 'Execution successful.', 'success': True}
        )
        self.patcher_super_agent.return_value = self.mock_super_agent_instance

        # Patch asyncio.run since it's called by cmd_run
        self.patcher_asyncio_run = patch('wai_cli.asyncio.run').start()
        def fake_asyncio_run(coroutine):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coroutine)
            finally:
                loop.close()
                asyncio.set_event_loop(None)

        self.patcher_asyncio_run.side_effect = fake_asyncio_run

        # Capture stdout and stderr
        self.held_output = io.StringIO()
        self.patcher_stdout = patch('sys.stdout', new=self.held_output).start()
        self.patcher_stderr = patch('sys.stderr', new=io.StringIO()).start() # Mock stderr too


    def tearDown(self):
        patch.stopall()
        sys.stdout = sys.__stdout__ # Restore stdout
        sys.stderr = sys.__stderr__ # Restore stderr

    def test_list_command(self):
        exit_code = self.app.run(['list'])
        self.assertEqual(exit_code, 0)
        # Verify playbook manager interaction
        self.mock_playbook_manager.get_playbook_summary.assert_called_once()
        # Basic check of output content (should contain playbook title)
        output = self.held_output.getvalue()
        self.assertIn('Available Playbooks:', output)
        self.assertIn('Test Playbook', output)

    def test_select_command(self):
        exit_code = self.app.run(['select', 'test-playbook'])
        self.assertEqual(exit_code, 0)
        # Verify playbook manager interaction
        self.mock_playbook_manager.get_playbook.assert_called_once_with('test-playbook')
        # Basic check of output format (should be YAML by default)
        output = self.held_output.getvalue()
        self.assertIn('id: test-playbook', output)
        self.assertIn('title: Test Playbook', output)

    def test_describe_command(self):
        exit_code = self.app.run(['describe', 'test-playbook'])
        self.assertEqual(exit_code, 0)
        # Verify playbook manager interaction
        self.mock_playbook_manager.get_playbook_parameters.assert_called_once_with('test-playbook')
        # Basic check of output format (should be table by default)
        output = self.held_output.getvalue()
        self.assertIn('Parameters for playbook 'test-playbook':', output)
        self.assertIn('param1', output)
        self.assertIn('string', output)

    def test_run_command_success(self):
        exit_code = self.app.run(['run', 'test-playbook'])
        self.assertEqual(exit_code, 0)
        # Verify interactions
        self.patcher_pydantic_ai_check.assert_called_once() # Pydantic AI checked
        self.mock_playbook_manager.get_playbook.assert_called_once_with('test-playbook') # Playbook retrieved
        # Check if SuperAgent was initialized and execute_playbook was called
        self.patcher_super_agent.assert_called_once_with(
            verbose=False, model=None, mcp_config_path=None # Default args
        )
        self.mock_super_agent_instance.set_message_callback.assert_called_once()
        self.mock_super_agent_instance.set_progress_callback.assert_called_once()
        self.mock_super_agent_instance.execute_playbook.assert_called_once_with(
             mock_playbook, None # Default parameters
        )
        # Check output
        output = self.held_output.getvalue()
        self.assertIn('Playbook execution completed successfully!', output)
        self.assertIn('--- Playbook Result ---', output)
        self.assertIn('Execution successful.', output)

    def test_run_command_with_args(self):
         # Configure execute_playbook to return a successful result with specific params
        self.mock_super_agent_instance.execute_playbook = AsyncMock(
            return_value={'result': 'Execution with params success.', 'success': True}
        )

        exit_code = self.app.run([
            'run', 'test-playbook',
            '--verbose',
            '--model', 'gpt-4',
            '--mcp-config', './config.json',
            '--param', 'param1=value1',
            '--param', 'param2=123',
            '--log-file', '/tmp/test.log'
        ])
        self.assertEqual(exit_code, 0)

        # Verify interactions
        self.patcher_pydantic_ai_check.assert_called_once() # Pydantic AI checked
        self.mock_playbook_manager.get_playbook.assert_called_once_with('test-playbook') # Playbook retrieved
        
        # Check if SuperAgent was initialized with correct args
        self.patcher_super_agent.assert_called_once_with(
            verbose=True, model='gpt-4', mcp_config_path='./config.json'
        )
        self.mock_super_agent_instance.set_message_callback.assert_called_once()
        self.mock_super_agent_instance.set_progress_callback.assert_called_once()

        # Check if execute_playbook was called with correct playbook and parameters
        self.mock_super_agent_instance.execute_playbook.assert_called_once_with(
             mock_playbook, {'param1': 'value1', 'param2': '123'} # Parsed parameters
        )
        
        # Check output
        output = self.held_output.getvalue()
        self.assertIn('Playbook execution completed successfully!', output)
        self.assertIn('--- Playbook Result ---', output)
        self.assertIn('Execution with params success.', output)
        self.assertIn('Full execution log saved to: /tmp/test.log', output) # Verify log file message

    def test_run_command_execution_failure(self):
         # Configure execute_playbook to return a failure result
        self.mock_super_agent_instance.execute_playbook = AsyncMock(
            return_value={'error': 'Execution failed.', 'success': False}
        )
        exit_code = self.app.run(['run', 'test-playbook'])
        self.assertEqual(exit_code, 1) # Should return non-zero on failure

        # Verify interactions
        self.patcher_pydantic_ai_check.assert_called_once()
        self.mock_playbook_manager.get_playbook.assert_called_once_with('test-playbook')
        self.patcher_super_agent.assert_called_once()
        self.mock_super_agent_instance.execute_playbook.assert_called_once_with(
             mock_playbook, None
        )
        # Check output (error message logged by CLI)
        self.app.logger.error.assert_called_with('Playbook execution failed: Execution failed.')

    def test_run_command_playbook_not_found(self):
        # Configure playbook manager to return None
        self.mock_playbook_manager.get_playbook.return_value = None
        
        exit_code = self.app.run(['run', 'nonexistent-playbook'])
        self.assertEqual(exit_code, 1) # Should return non-zero if playbook not found
        
        # Verify interactions
        self.patcher_pydantic_ai_check.assert_called_once()
        self.mock_playbook_manager.get_playbook.assert_called_once_with('nonexistent-playbook')
        # SuperAgent should not be initialized or called
        self.patcher_super_agent.assert_not_called()
        self.mock_super_agent_instance.execute_playbook.assert_not_called()
        
        # Check output (error message logged by CLI)
        self.app.logger.error.assert_called_with('Playbook not found: nonexistent-playbook')


if __name__ == '__main__':
    unittest.main()
