from typing import List, Dict, Any, Optional, Union, Callable
from pydantic import BaseModel, Field
import pytest
import unittest
import json
import os
import sys
import importlib
import inspect
from pathlib import Path
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCase(BaseModel):
    """Model for a single test case"""
    name: str = Field(..., description="Name of the test case")
    description: str = Field(..., description="Description of what is being tested")
    test_type: str = Field(..., description="Type of test (unit, integration, e2e)")
    inputs: Dict[str, Any] = Field(..., description="Test inputs")
    expected_outputs: Dict[str, Any] = Field(..., description="Expected outputs")
    dependencies: Optional[List[str]] = Field(default=None, description="Dependencies required for the test")
    timeout: Optional[int] = Field(default=30, description="Test timeout in seconds")
    priority: Optional[str] = Field(default="medium", description="Test priority (low, medium, high)")
    tags: Optional[List[str]] = Field(default=None, description="Tags for test categorization")
    setup_function: Optional[str] = Field(default=None, description="Name of setup function")
    teardown_function: Optional[str] = Field(default=None, description="Name of teardown function")

class TestEnvironment(BaseModel):
    """Model for test environment configuration"""
    name: str = Field(..., description="Environment name")
    variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    dependencies: List[str] = Field(default_factory=list, description="Required dependencies")
    python_version: str = Field(default="3.11", description="Required Python version")
    setup_commands: List[str] = Field(default_factory=list, description="Commands to run during setup")

class TestSuite(BaseModel):
    """Model for a test suite containing multiple test cases"""
    name: str = Field(..., description="Name of the test suite")
    description: str = Field(..., description="Description of the test suite")
    test_cases: List[TestCase] = Field(..., description="List of test cases in this suite")
    setup: Optional[Dict[str, Any]] = Field(default=None, description="Setup configuration for the suite")
    teardown: Optional[Dict[str, Any]] = Field(default=None, description="Teardown configuration for the suite")
    environment: Optional[TestEnvironment] = Field(default=None, description="Test environment configuration")
    parallel_execution: bool = Field(default=False, description="Whether tests can run in parallel")
    max_workers: Optional[int] = Field(default=None, description="Maximum number of parallel workers")
    dependencies: List[str] = Field(default_factory=list, description="Suite-level dependencies")

class TestResult(BaseModel):
    """Model for test execution results"""
    test_case_name: str = Field(..., description="Name of the test case")
    status: str = Field(..., description="Test status (passed, failed, error, skipped)")
    execution_time: float = Field(..., description="Time taken to execute the test in seconds")
    error_message: Optional[str] = Field(default=None, description="Error message if test failed")
    stack_trace: Optional[str] = Field(default=None, description="Stack trace if test failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Test execution timestamp")
    environment: Optional[Dict[str, str]] = Field(default=None, description="Environment details")
    outputs: Optional[Dict[str, Any]] = Field(default=None, description="Test outputs")

class TestTool:
    """Tool for managing and executing tests"""
    
    def __init__(self, base_path: str = "./tests"):
        self.base_path = Path(base_path)
        self.test_suites: Dict[str, TestSuite] = {}
        self.environments: Dict[str, TestEnvironment] = {}
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count())
        
    def create_test_suite(self, suite: TestSuite) -> bool:
        """Create a new test suite"""
        try:
            suite_path = self.base_path / f"{suite.name}"
            suite_path.mkdir(parents=True, exist_ok=True)
            
            # Save suite configuration
            with open(suite_path / "suite_config.json", "w") as f:
                json.dump(suite.dict(), f, indent=2)
                
            # Create test files
            self._generate_test_files(suite)
            
            # Create environment setup if specified
            if suite.environment:
                self._setup_environment(suite.environment, suite_path)
                
            self.test_suites[suite.name] = suite
            return True
        except Exception as e:
            logger.error(f"Error creating test suite: {str(e)}")
            return False
            
    def _setup_environment(self, env: TestEnvironment, suite_path: Path):
        """Set up the test environment"""
        env_path = suite_path / "environment"
        env_path.mkdir(exist_ok=True)
        
        # Create requirements.txt
        if env.dependencies:
            with open(env_path / "requirements.txt", "w") as f:
                f.write("\n".join(env.dependencies))
                
        # Create environment setup script
        if env.setup_commands:
            with open(env_path / "setup.sh", "w") as f:
                f.write("#!/bin/bash\n")
                f.write("\n".join(env.setup_commands))
            os.chmod(env_path / "setup.sh", 0o755)
            
        # Create environment variables file
        if env.variables:
            with open(env_path / ".env", "w") as f:
                for key, value in env.variables.items():
                    f.write(f"{key}={value}\n")
                    
    def _generate_test_files(self, suite: TestSuite):
        """Generate Python test files from test cases"""
        suite_path = self.base_path / f"{suite.name}"
        
        # Create __init__.py
        (suite_path / "__init__.py").touch()
        
        # Create conftest.py for pytest fixtures
        self._generate_conftest(suite, suite_path)
        
        # Create test files
        test_file_content = self._generate_test_file_content(suite)
        with open(suite_path / f"test_{suite.name}.py", "w") as f:
            f.write(test_file_content)
            
    def _generate_conftest(self, suite: TestSuite, suite_path: Path):
        """Generate conftest.py with pytest fixtures"""
        content = [
            "import pytest",
            "import os",
            "import json",
            "from pathlib import Path\n",
            "# Load suite configuration",
            "with open(Path(__file__).parent / 'suite_config.json') as f:",
            "    SUITE_CONFIG = json.load(f)\n",
            "@pytest.fixture(scope='session')",
            "def suite_setup():",
            "    # Implement suite-level setup",
            "    if SUITE_CONFIG.get('setup'):  # type: ignore",
            "        # Add setup implementation",
            "        pass",
            "    yield",
            "    # Implement suite-level teardown",
            "    if SUITE_CONFIG.get('teardown'):  # type: ignore",
            "        # Add teardown implementation",
            "        pass\n"
        ]
        
        with open(suite_path / "conftest.py", "w") as f:
            f.write("\n".join(content))
            
    def _generate_test_file_content(self, suite: TestSuite) -> str:
        """Generate the content for a test file"""
        content = [
            "import pytest",
            "import unittest",
            "import json",
            "import os",
            "from typing import Dict, Any",
            "from pathlib import Path\n",
            f"class Test{suite.name.title()}(unittest.TestCase):",
            f'    """Test suite for {suite.name}"""\n',
            "    @classmethod",
            "    def setUpClass(cls):",
            "        cls.suite_config = json.load(open(Path(__file__).parent / 'suite_config.json'))",
            "        if cls.suite_config.get('environment', {}).get('variables'):",
            "            for key, value in cls.suite_config['environment']['variables'].items():",
            "                os.environ[key] = value\n",
            "    @classmethod",
            "    def tearDownClass(cls):",
            "        # Clean up environment variables",
            "        if cls.suite_config.get('environment', {}).get('variables'):",
            "            for key in cls.suite_config['environment']['variables'].keys():",
            "                os.environ.pop(key, None)\n"
        ]
        
        # Add test methods
        for case in suite.test_cases:
            content.extend([
                f"    def test_{case.name}(self):",
                f'        """Test: {case.description}"""',
                "        try:",
                f"            test_case = next(tc for tc in self.suite_config['test_cases'] if tc['name'] == '{case.name}')",
                "            inputs = test_case['inputs']",
                "            expected = test_case['expected_outputs']",
                "            # Add test implementation here",
                "            # self.assertEqual(actual, expected)",
                "            pass",
                "        except Exception as e:",
                "            self.fail(f'Test failed: {str(e)}')\n"
            ])
            
        return "\n".join(content)
        
    async def _run_tests_internal(self, suite_name: Optional[str] = None) -> List[TestResult]:
        """Internal method to run tests for a specific suite or all suites"""
        results = []

        if suite_name and suite_name in self.test_suites:
            results.extend(await self._run_suite(self.test_suites[suite_name]))
        elif not suite_name:
            # Run suites in parallel if possible
            tasks = [
                self._run_suite(suite)
                for suite in self.test_suites.values()
            ]
            suite_results = await asyncio.gather(*tasks)
            for suite_result in suite_results:
                results.extend(suite_result)

        return results
        
async def run_tests(test_suite: Optional[str] = None, environment: Optional[Any] = None, parallel: bool = False) -> List[Dict[str, Any]]:
    """
    Runs tests for a specific suite or all suites as a tool entry point.

    Args:
        test_suite: The name of the test suite to run. If None, all suites are run.
        environment: Test environment configuration (usage unclear from existing code).
        parallel: Whether to run tests in parallel (usage unclear from existing code).

    Returns:
        A list of dictionaries representing the test results.
    """
    # Instantiate TestTool. How test suites are provided to this instance
    # is not fully clear from the current code, assuming default behavior.
    # The 'environment' and 'parallel' parameters from tools.yaml are not
    # directly used by _run_tests_internal and may require further
    # integration into the TestTool class or this function if needed.
    test_tool_instance = TestTool()
    results = await test_tool_instance._run_tests_internal(suite_name=test_suite)

    # Convert TestResult objects to dictionaries for tool response
    return [r.dict() for r in results]

    async def _run_suite(self, suite: TestSuite) -> List[TestResult]:
        """Run all tests in a suite"""
        results = []
        suite_path = self.base_path / f"{suite.name}"
        
        # Set up test environment if specified
        if suite.environment:
            self._setup_test_environment(suite)
            
        try:
            # Import test module
            sys.path.insert(0, str(suite_path))
            module_name = f"test_{suite.name}"
            module = importlib.import_module(module_name)
            
            # Get test class
            test_class = getattr(module, f"Test{suite.name.title()}")
            
            # Run tests
            if suite.parallel_execution:
                results = await self._run_parallel_tests(test_class, suite)
            else:
                results = await self._run_sequential_tests(test_class, suite)
                
        except Exception as e:
            logger.error(f"Error running test suite {suite.name}: {str(e)}")
            results.append(
                TestResult(
                    test_case_name=suite.name,
                    status="error",
                    execution_time=0.0,
                    error_message=str(e),
                    stack_trace=traceback.format_exc()
                )
            )
        finally:
            # Clean up
            sys.path.remove(str(suite_path))
            
        return results
        
    def _setup_test_environment(self, suite: TestSuite):
        """Set up the test environment for a suite"""
        if not suite.environment:
            return
            
        env_path = self.base_path / suite.name / "environment"
        
        # Install dependencies
        if os.path.exists(env_path / "requirements.txt"):
            os.system(f"pip install -r {env_path / 'requirements.txt'}")
            
        # Run setup script
        if os.path.exists(env_path / "setup.sh"):
            os.system(f"bash {env_path / 'setup.sh'}")
            
        # Load environment variables
        if os.path.exists(env_path / ".env"):
            with open(env_path / ".env") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value
                        
    async def _run_parallel_tests(self, test_class, suite: TestSuite) -> List[TestResult]:
        """Run tests in parallel"""
        results = []
        max_workers = suite.max_workers or os.cpu_count()
        
        async def run_test(test_name: str) -> TestResult:
            test_instance = test_class()
            test_method = getattr(test_instance, test_name)
            
            start_time = datetime.now()
            try:
                await asyncio.get_event_loop().run_in_executor(
                    self.executor, test_method
                )
                status = "passed"
                error_message = None
                stack_trace = None
            except Exception as e:
                status = "failed"
                error_message = str(e)
                stack_trace = traceback.format_exc()
                
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TestResult(
                test_case_name=test_name,
                status=status,
                execution_time=execution_time,
                error_message=error_message,
                stack_trace=stack_trace
            )
            
        # Get all test methods
        test_methods = [
            name for name, _ in inspect.getmembers(test_class, predicate=inspect.isfunction)
            if name.startswith("test_")
        ]
        
        # Run tests in parallel
        tasks = [run_test(method) for method in test_methods]
        results = await asyncio.gather(*tasks)
        
        return results
        
    async def _run_sequential_tests(self, test_class, suite: TestSuite) -> List[TestResult]:
        """Run tests sequentially"""
        results = []
        test_instance = test_class()
        
        # Run tests
        for case in suite.test_cases:
            test_name = f"test_{case.name}"
            if not hasattr(test_instance, test_name):
                continue
                
            test_method = getattr(test_instance, test_name)
            
            start_time = datetime.now()
            try:
                await asyncio.get_event_loop().run_in_executor(
                    self.executor, test_method
                )
                status = "passed"
                error_message = None
                stack_trace = None
            except Exception as e:
                status = "failed"
                error_message = str(e)
                stack_trace = traceback.format_exc()
                
            execution_time = (datetime.now() - start_time).total_seconds()
            
            results.append(
                TestResult(
                    test_case_name=case.name,
                    status=status,
                    execution_time=execution_time,
                    error_message=error_message,
                    stack_trace=stack_trace,
                    environment=dict(os.environ) if suite.environment else None
                )
            )
            
        return results
        
    def generate_report(self, results: List[TestResult], format: str = "text") -> str:
        """Generate a test report in the specified format"""
        if format == "text":
            return self._generate_text_report(results)
        elif format == "json":
            return json.dumps([r.dict() for r in results], indent=2, default=str)
        else:
            raise ValueError(f"Unsupported report format: {format}")
            
    def _generate_text_report(self, results: List[TestResult]) -> str:
        """Generate a text-based test report"""
        report = ["Test Execution Report", "===================\n"]
        
        # Summary
        total = len(results)
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        errors = sum(1 for r in results if r.status == "error")
        skipped = sum(1 for r in results if r.status == "skipped")
        
        report.extend([
            f"Total Tests: {total}",
            f"Passed: {passed}",
            f"Failed: {failed}",
            f"Errors: {errors}",
            f"Skipped: {skipped}\n",
            "Detailed Results:",
            "----------------\n"
        ])
        
        # Detailed results
        for result in results:
            report.extend([
                f"Test: {result.test_case_name}",
                f"Status: {result.status}",
                f"Time: {result.execution_time:.2f}s",
                f"Timestamp: {result.timestamp}"
            ])
            
            if result.environment:
                report.append("Environment Variables:")
                for key, value in result.environment.items():
                    report.append(f"  {key}={value}")
                    
            if result.error_message:
                report.extend([
                    "Error Message:",
                    result.error_message
                ])
                
            if result.stack_trace:
                report.extend([
                    "Stack Trace:",
                    result.stack_trace
                ])
                
            report.append("")
            
        return "\n".join(report) 