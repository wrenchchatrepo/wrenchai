#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import unittest
from unittest.mock import patch, MagicMock, AsyncMock, call
import sys
import asyncio

# Add the wrenchai directory to the sys.path to allow importing modules
sys.path.insert(0, '.')

from wai_cli import WrenchAICliApp

# Mock SuperAgent class (now using MagicMock for easier assertion)
# class MockSuperAgent:
#     def __init__(self, verbose=False, model=None, mcp_config_path=None):
#         self.verbose = verbose
#         self.model = model
#         self.mcp_config_path = mcp_config_path
#         self._message_callback = None
#         self._progress_callback = None

#     def set_message_callback(self, callback):
#         self._message_callback = callback

#     def set_progress_callback(self, callback):
#         self._progress_callback = callback

#     async def execute_playbook(self, playbook, parameters=None):
#         # Simulate some async work
#         await asyncio.sleep(0.01)
#         # Return a mock result
#         return {"result": "Mock Playbook Result", "success": True}


class TestCliRunCommand(unittest.TestCase):

    def setUp(self):
        self.app = WrenchAICliApp()
        self.app.logger = MagicMock() # Mock logger to prevent output during tests

        # Mock asyncio.run since it's called by cmd_run
        self.mock_asyncio_run = patch('wai_cli.asyncio.run').start()
        # Configure mock_asyncio_run to call the actual async method with a mock loop
        # This is a common pattern when testing async functions called by a sync wrapper
        def fake_asyncio_run(coroutine):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coroutine)
            finally:
                loop.close()
                asyncio.set_event_loop(None)

        self.mock_asyncio_run.side_effect = fake_asyncio_run

        # Patch SuperAgent class creation
        self.mock_super_agent_cls = patch('core.super_agent.SuperAgent').start()
        # Create an instance mock and configure its execute_playbook method
        self.mock_super_agent_instance = MagicMock()
        self.mock_super_agent_instance.execute_playbook = AsyncMock(
            return_value={'result': 'Mock Playbook Result', 'success': True}
        )
        # Configure the mock class to return the instance mock when called
        self.mock_super_agent_cls.return_value = self.mock_super_agent_instance

        # Mock get_playbook_manager
        self.mock_get_playbook_manager = patch('core.playbook_discovery.get_playbook_manager').start()
        self.mock_manager_instance = MagicMock()
        self.mock_manager_instance.get_playbook.return_value = {
            'id': 'test-playbook',
            'title': 'Test Playbook',
            'description': 'A playbook for testing',
            'steps': []
        }
        self.mock_get_playbook_manager.return_value = self.mock_manager_instance
        
        # Mock _check_pydantic_ai to always return True
        self.mock_check_pydantic_ai = patch.object(self.app, '_check_pydantic_ai', return_value=True).start()


    def tearDown(self):
        patch.stopall()
        
    def test_cmd_run_success(self):
        # Create mock args for the run command
        mock_args = MagicMock()
        mock_args.id = 'test-playbook'
        mock_args.params = None
        mock_args.verbose = False
        mock_args.model = None
        mock_args.mcp_config = None
        mock_args.log_file = None

        # Call the cmd_run method
        exit_code = self.app.cmd_run(mock_args)

        # Assertions
        self.assertEqual(exit_code, 0)
        self.mock_check_pydantic_ai.assert_called_once() # Pydantic AI availability checked
        self.mock_get_playbook_manager.assert_called_once() # Playbook manager called
        self.mock_manager_instance.get_playbook.assert_called_once_with('test-playbook') # Playbook retrieved
        
        # Check SuperAgent initialization (default args)
        self.mock_super_agent_cls.assert_called_once_with(
            verbose=False,
            model=None,
            mcp_config_path=None
        )
        
        # Check if callbacks were set
        self.mock_super_agent_instance.set_message_callback.assert_called_once()
        self.mock_super_agent_instance.set_progress_callback.assert_called_once()

        # Check if execute_playbook was called with correct args
        self.mock_super_agent_instance.execute_playbook.assert_called_once_with(
            {
            'id': 'test-playbook',
            'title': 'Test Playbook',
            'description': 'A playbook for testing',
            'steps': []
            },
            None
        )
        
        # Ensure no errors were logged
        self.app.logger.error.assert_not_called()
        self.app.logger.warning.assert_not_called()


    def test_cmd_run_playbook_not_found(self):
        # Mock playbook manager to return None (playbook not found)
        self.mock_manager_instance.get_playbook.return_value = None

        # Create mock args for the run command
        mock_args = MagicMock()
        mock_args.id = 'nonexistent-playbook'
        mock_args.params = None
        mock_args.verbose = False
        mock_args.model = None
        mock_args.mcp_config = None
        mock_args.log_file = None
        
        # Call the cmd_run method
        exit_code = self.app.cmd_run(mock_args)

        # Assertions
        self.assertEqual(exit_code, 1) # Should exit with error code
        self.mock_check_pydantic_ai.assert_called_once()
        self.mock_get_playbook_manager.assert_called_once()
        self.mock_manager_instance.get_playbook.assert_called_once_with('nonexistent-playbook')
        self.app.logger.error.assert_called_with('Playbook not found: nonexistent-playbook') # Should log an error
        
        # Ensure SuperAgent was not initialized or called
        self.mock_super_agent_cls.assert_not_called()
        self.mock_super_agent_instance.execute_playbook.assert_not_called()

    def test_cmd_run_with_parameters(self):
        # Configure execute_playbook to return success
        self.mock_super_agent_instance.execute_playbook = AsyncMock(
            return_value={'result': 'Result with params', 'success': True}
        )
        
        # Create mock args with parameters
        mock_args = MagicMock()
        mock_args.id = 'test-playbook'
        mock_args.params = ['param1=value1', 'param2=123']
        mock_args.verbose = False
        mock_args.model = None
        mock_args.mcp_config = None
        mock_args.log_file = None

        # Call the cmd_run method
        exit_code = self.app.cmd_run(mock_args)

        # Assertions
        self.assertEqual(exit_code, 0)
        self.mock_check_pydantic_ai.assert_called_once()
        self.mock_get_playbook_manager.assert_called_once()
        self.mock_manager_instance.get_playbook.assert_called_once_with('test-playbook')
        
        # Check SuperAgent initialization (default args)
        self.mock_super_agent_cls.assert_called_once_with(
            verbose=False,
            model=None,
            mcp_config_path=None
        )
        
        # Check if callbacks were set
        self.mock_super_agent_instance.set_message_callback.assert_called_once()
        self.mock_super_agent_instance.set_progress_callback.assert_called_once()

        # Check if execute_playbook was called with parsed parameters
        self.mock_super_agent_instance.execute_playbook.assert_called_once_with(
            {
            'id': 'test-playbook',
            'title': 'Test Playbook',
            'description': 'A playbook for testing',
            'steps': []
            },
            {'param1': 'value1', 'param2': '123'} # Parsed parameters
        )
        
        self.app.logger.error.assert_not_called()
        self.app.logger.warning.assert_not_called()

    def test_cmd_run_execution_failure(self):
        # Configure execute_playbook to return failure
        self.mock_super_agent_instance.execute_playbook = AsyncMock(
            return_value={'error': 'Mock Execution Error', 'success': False}
        )
        
        # Create mock args
        mock_args = MagicMock()
        mock_args.id = 'test-playbook'
        mock_args.params = None
        mock_args.verbose = False
        mock_args.model = None
        mock_args.mcp_config = None
        mock_args.log_file = None

        # Call the cmd_run method
        exit_code = self.app.cmd_run(mock_args)

        # Assertions
        self.assertEqual(exit_code, 1) # Should exit with error code
        self.mock_check_pydantic_ai.assert_called_once()
        self.mock_get_playbook_manager.assert_called_once()
        self.mock_manager_instance.get_playbook.assert_called_once_with('test-playbook')
        self.mock_super_agent_cls.assert_called_once() # SuperAgent should be initialized
        self.mock_super_agent_instance.execute_playbook.assert_called_once() # execute_playbook should be called
        
        # Check that an error was logged
        self.app.logger.error.assert_called_with('Playbook execution failed: Mock Execution Error')
        
    def test_cmd_run_super_agent_init_args(self):
        # Create mock args with specific values for SuperAgent constructor
        mock_args = MagicMock()
        mock_args.id = 'test-playbook'
        mock_args.params = None
        mock_args.verbose = True
        mock_args.model = 'anthropic:claude-3'
        mock_args.mcp_config = '/custom/mcp_config.json'
        mock_args.log_file = None

        # Call the cmd_run method
        exit_code = self.app.cmd_run(mock_args)

        # Assertions
        self.assertEqual(exit_code, 0)
        self.mock_check_pydantic_ai.assert_called_once()
        self.mock_get_playbook_manager.assert_called_once()
        self.mock_manager_instance.get_playbook.assert_called_once_with('test-playbook')
        
        # Check SuperAgent initialization arguments
        self.mock_super_agent_cls.assert_called_once_with(
            verbose=True,
            model='anthropic:claude-3',
            mcp_config_path='/custom/mcp_config.json'
        )
        
        self.mock_super_agent_instance.execute_playbook.assert_called_once()
        self.app.logger.error.assert_not_called()

    def test_cmd_run_callbacks_set(self):
        # Create mock args
        mock_args = MagicMock()
        mock_args.id = 'test-playbook'
        mock_args.params = None
        mock_args.verbose = False
        mock_args.model = None
        mock_args.mcp_config = None
        mock_args.log_file = None

        # Call the cmd_run method
        exit_code = self.app.cmd_run(mock_args)

        # Assertions
        self.assertEqual(exit_code, 0)
        self.mock_check_pydantic_ai.assert_called_once()
        self.mock_get_playbook_manager.assert_called_once()
        self.mock_manager_instance.get_playbook.assert_called_once_with('test-playbook')
        
        # Check if set_message_callback and set_progress_callback were called
        # We can't easily assert the *exact* function object passed due to them being lambdas/nested
        # but we can check they were called exactly once.
        self.mock_super_agent_instance.set_message_callback.assert_called_once()
        self.mock_super_agent_instance.set_progress_callback.assert_called_once()
        self.mock_super_agent_instance.execute_playbook.assert_called_once()
        
        self.app.logger.error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
