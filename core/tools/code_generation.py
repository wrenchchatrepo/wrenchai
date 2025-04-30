# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import json
from typing import Dict, Any, Optional, List, Union, Literal
from pathlib import Path
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class CodeSpec(BaseModel):
    """Specification for code generation."""
    description: str = Field(..., description="Description of what needs to be generated")
    requirements: list[str] = Field(default_factory=list, description="List of requirements")
    dependencies: list[str] = Field(default_factory=list, description="Required dependencies")
    examples: list[str] = Field(default_factory=list, description="Example usage")
    tests: bool = Field(default=True, description="Whether to generate tests")
    docs: bool = Field(default=True, description="Whether to generate documentation")

class GenerationContext(BaseModel):
    """Context for code generation."""
    project_type: str = Field(..., description="Type of project (library, application, etc.)")
    style_guide: str = Field(default="pep8", description="Code style guide to follow")
    test_framework: str = Field(default="pytest", description="Test framework to use")
    doc_format: str = Field(default="google", description="Documentation format")
    additional_context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

class GeneratedCode(BaseModel):
    """Result of code generation."""
    code: str = Field(..., description="Generated code")
    tests: Optional[str] = Field(None, description="Generated tests")
    docs: Optional[str] = Field(None, description="Generated documentation")
    dependencies: list[str] = Field(default_factory=list, description="Required dependencies")
    setup_instructions: Optional[str] = Field(None, description="Setup instructions")

OutputType = Literal["code", "tests", "docs", "all"]

async def generate(
    spec: CodeSpec,
    language: str,
    framework: str,
    output_type: OutputType = "all",
    context: Optional[GenerationContext] = None
) -> GeneratedCode:
    """
    Asynchronously generates source code, tests, and documentation from a specification.
    
    Depending on the provided output type and flags in the specification, this function produces code, tests, and documentation for the specified language and framework, using the given or default generation context. It also determines required dependencies and setup instructions.
    
    Args:
        spec: The code generation specification.
        language: Target programming language.
        framework: Target framework or library.
        output_type: Specifies which outputs to generate ("code", "tests", "docs", or "all").
        context: Optional generation context; defaults to a library project if not provided.
    
    Returns:
        A GeneratedCode instance containing the generated code, tests, documentation, dependencies, and setup instructions.
    """
    try:
        # Initialize context if not provided
        context = context or GenerationContext(project_type="library")
        
        # Get appropriate model for the language/framework
        model = _get_generation_model(language, framework)
        
        # Generate code
        code = await _generate_code(spec, model, context) if output_type in ["code", "all"] else ""
        
        # Generate tests if requested
        tests = await _generate_tests(code, spec, model, context) if output_type in ["tests", "all"] and spec.tests else None
        
        # Generate documentation if requested
        docs = await _generate_docs(code, spec, model, context) if output_type in ["docs", "all"] and spec.docs else None
        
        # Determine required dependencies
        dependencies = await _get_dependencies(code, language, framework)
        
        # Generate setup instructions
        setup = await _generate_setup_instructions(dependencies, language, framework)
        
        return GeneratedCode(
            code=code,
            tests=tests,
            docs=docs,
            dependencies=dependencies,
            setup_instructions=setup
        )
        
    except Exception as e:
        logger.error(f"Code generation failed: {str(e)}")
        raise

async def _get_generation_model(language: str, framework: str) -> Any:
    """
    Retrieves the code generation model for the specified language and framework.
    
    Currently returns a placeholder; intended for integration with actual code generation services.
    """
    # This would integrate with your preferred code generation model/service
    # For now, we'll use a placeholder
    return None

async def _generate_code(spec: CodeSpec, model: Any, context: GenerationContext) -> str:
    """
    Generates source code from the provided specification using the given model and context.
    
    Args:
        spec: The code generation specification.
        model: The code generation model to use.
        context: The context for code generation.
    
    Returns:
        The generated source code as a string.
    """
    # This would use the model to generate actual code
    # For now, return a placeholder
    return "# Generated code placeholder"

async def _generate_tests(
    code: str,
    spec: CodeSpec,
    model: Any,
    context: GenerationContext
) -> str:
    """
    Generates test code for the specified source code and specification.
    
    Selects an appropriate test template based on the target language and framework, formats test components such as fixtures, setup, arrange, act, and assertions, and returns the generated test code along with metadata. If the language or framework is unsupported, returns an error dictionary.
    """
    test_templates = {
        'python': {
            'pytest': '''import pytest
from {module} import {name}

{fixtures}

def test_{name}_{scenario}():
    """Test {name} {scenario}"""
    {arrange}
    {act}
    {assert_block}''',
            'unittest': '''import unittest
from {module} import {name}

class Test{name}(unittest.TestCase):
    {setup}
    
    def test_{scenario}(self):
        """Test {name} {scenario}"""
        {arrange}
        {act}
        {assert_block}'''
        },
        'typescript': {
            'jest': '''import { {name} } from '{module}'

describe('{name}', () => {
  {before_each}
  
  test('{scenario}', () => {
    {arrange}
    {act}
    {assert_block}
  })
})''',
            'mocha': '''import { expect } from 'chai'
import { {name} } from '{module}'

describe('{name}', () => {
  {before_each}
  
  it('{scenario}', () => {
    {arrange}
    {act}
    {assert_block}
  })
})'''
        }
    }
    
    try:
        if language not in test_templates:
            raise ValueError(f'Unsupported language: {language}')
            
        if framework not in test_templates[language]:
            framework = list(test_templates[language].keys())[0]
            
        template = test_templates[language][framework]
        
        # Helper functions to format test components
        def _format_fixtures(fixtures: List[str], lang: str) -> str:
            """
            Formats test fixture definitions for the specified language.
            
            Args:
                fixtures: A list of fixture names.
                lang: The programming language for which to format the fixtures.
            
            Returns:
                A string containing formatted fixture definitions, or an empty string if no fixtures are provided or the language is unsupported.
            """
            if not fixtures:
                return ""
                
            if lang == 'python':
                return "\n".join(f"@pytest.fixture\ndef {f}():\n    return {fixtures[f]}" 
                               for f in fixtures)
            return ""
            
        def _format_setup(setup: List[str], lang: str) -> str:
            """
            Formats setup code statements for inclusion in test functions.
            
            Args:
                setup: List of setup statements.
                lang: Target programming language ("python" or "typescript").
            
            Returns:
                A formatted string of setup statements with appropriate indentation for the specified language.
            """
            if not setup:
                return ""
                
            if lang == 'python':
                return "\n    ".join(setup)
            elif lang == 'typescript':
                return "\n  ".join(setup)
            return ""
            
        def _format_arrange(arrange: List[str], lang: str) -> str:
            """
            Formats the arrangement section of a test case for the specified language.
            
            Args:
                arrange: List of statements to set up test conditions.
                lang: Target programming language ('python' or 'typescript').
            
            Returns:
                A formatted string representing the arrange block, properly indented for the language.
            """
            if not arrange:
                return "pass" if lang == 'python' else ""
                
            if lang == 'python':
                return "\n    ".join(arrange)
            elif lang == 'typescript':
                return "\n    ".join(arrange)
            return ""
            
        def _format_act(act: List[str], lang: str) -> str:
            """
            Formats the action section of a test case for the specified programming language.
            
            Args:
                act: List of action statements to include in the test.
                lang: Target programming language ('python' or 'typescript').
            
            Returns:
                A formatted string representing the action steps, properly indented for the language.
                Returns 'pass' for Python if no actions are provided, or an empty string for TypeScript.
            """
            if not act:
                return "pass" if lang == 'python' else ""
                
            if lang == 'python':
                return "\n    ".join(act)
            elif lang == 'typescript':
                return "\n    ".join(act)
            return ""
            
        def _format_assertions(assertions: List[str], lang: str) -> str:
            """
            Formats a list of assertion statements for inclusion in test code.
            
            Args:
                assertions: A list of assertion statements as strings.
                lang: The programming language ('python' or 'typescript').
            
            Returns:
                A formatted string of assertions suitable for the specified language. If no assertions are provided, returns a default assertion for the language.
            """
            if not assertions:
                return "assert True" if lang == 'python' else "expect(true).toBe(true)"
                
            if lang == 'python':
                return "\n    ".join(assertions)
            elif lang == 'typescript':
                return "\n    ".join(assertions)
            return ""
        
        # Extract test components from spec
        module = spec.module if hasattr(spec, 'module') else spec.get('module', '')
        name = spec.name if hasattr(spec, 'name') else spec.get('name', '')
        scenario = spec.scenario if hasattr(spec, 'scenario') else spec.get('scenario', 'basic')
        fixtures = spec.fixtures if hasattr(spec, 'fixtures') else spec.get('fixtures', [])
        setup = spec.setup if hasattr(spec, 'setup') else spec.get('setup', [])
        arrange = spec.arrange if hasattr(spec, 'arrange') else spec.get('arrange', [])
        act = spec.act if hasattr(spec, 'act') else spec.get('act', [])
        assertions = spec.assertions if hasattr(spec, 'assertions') else spec.get('assertions', [])
        
        # Generate test code using template
        code = template.format(
            module=module,
            name=name,
            scenario=scenario,
            fixtures=_format_fixtures(fixtures, language),
            setup=_format_setup(setup, language),
            arrange=_format_arrange(arrange, language),
            act=_format_act(act, language),
            assert_block=_format_assertions(assertions, language)
        )
        
        return {
            'code': code,
            'language': language,
            'framework': framework,
            'type': 'test'
        }
    except Exception as e:
        return {
            'error': str(e),
            'code': '',
            'language': language,
            'framework': framework,
            'type': 'test'
        }

async def _generate_docs(
    code: str,
    spec: CodeSpec,
    model: Any,
    context: GenerationContext
) -> str:
    """
    Generates documentation for the provided source code based on the given specification and context.
    
    Args:
        code: The source code to document.
        spec: The code generation specification.
        model: The code generation model to use.
        context: The generation context, including documentation format and style.
    
    Returns:
        A string containing the generated documentation.
    """
    # This would generate documentation in the specified format
    # For now, return a placeholder
    return "# Generated documentation placeholder"

async def _get_dependencies(
    code: str,
    language: str,
    framework: str
) -> list[str]:
    """
    Analyzes the code to identify required dependencies for the specified language and framework.
    
    Args:
        code: The source code to analyze.
        language: The programming language of the code.
        framework: The framework associated with the code.
    
    Returns:
        A list of dependencies required by the code.
    """
    # This would analyze the code and determine required dependencies
    # For now, return a placeholder
    return [framework]

async def _generate_setup_instructions(
    dependencies: list[str],
    language: str,
    framework: str
) -> str:
    """
    Generates environment setup instructions based on dependencies, language, and framework.
    
    Args:
        dependencies: List of required dependencies.
        language: Target programming language.
        framework: Target framework.
    
    Returns:
        A string containing setup instructions for installing dependencies and configuring the environment.
    """
    # This would generate instructions for setting up the environment
    # For now, return a placeholder
    return "# Setup instructions placeholder"

def _generate(
    spec: Union[CodeSpec, Dict[str, Any]],
    language: str,
    framework: str = '',
    output_type: str = 'source',
    context: Optional[Union[GenerationContext, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generates source code, tests, or documentation based on the provided specification.
    
    Args:
        spec: The code generation specification as a CodeSpec instance or dictionary.
        language: The target programming language ("python" or "typescript").
        framework: The framework to use for generation (e.g., "pytest", "jest").
        output_type: The type of output to generate ("source", "test", or "docs").
        context: Optional generation context as a GenerationContext instance or dictionary.
    
    Returns:
        A dictionary containing the generated code, language, framework, output type, and any error message if generation fails.
    """
    # Convert spec to CodeSpec if needed
    if isinstance(spec, dict):
        spec = CodeSpec(**spec)
        
    # Convert context to GenerationContext if needed
    if context is None:
        context = GenerationContext(project_type="library")
    elif isinstance(context, dict):
        context = GenerationContext(**context)
        
    # Validate language
    if language not in ['python', 'typescript']:
        return {
            'error': f'Unsupported language: {language}',
            'code': '',
            'language': language,
            'framework': framework,
            'type': output_type
        }
        
    # Generate based on output type
    if output_type == 'source':
        return _generate_source(spec, language, framework, context)
    elif output_type == 'test':
        return _generate_test(spec, language, framework, context)
    elif output_type == 'docs':
        return _generate_docs(spec, language, framework, context)
    else:
        return {
            'error': f'Unsupported output type: {output_type}',
            'code': '',
            'language': language,
            'framework': framework,
            'type': output_type
        }

def _generate_source(
    spec: CodeSpec,
    language: str,
    framework: str,
    context: GenerationContext
) -> Dict[str, Any]:
    """
    Generates source code based on the provided specification, language, and framework.
    
    Returns:
        A dictionary containing the generated source code, language, framework, and type.
        If an error occurs, the dictionary includes an 'error' field with the error message.
    """
    code_templates = {
        'python': {
            'class': '''class {name}:
    """{docstring}"""
    
    def __init__(self{params}):
        {init_body}
        
    {methods}''',
            'function': '''def {name}({params}) -> {return_type}:
    """{docstring}"""
    {body}''',
            'module': '''"""
{module_docstring}
"""

{imports}

{code}
'''
        },
        'typescript': {
            'class': '''class {name} {
  {properties}
  
  constructor({params}) {
    {init_body}
  }
  
  {methods}
}''',
            'function': '''function {name}({params}): {return_type} {
  {body}
}''',
            'module': '''/**
 * {module_docstring}
 */

{imports}

{code}
'''
        }
    }
    
    try:
        # Generate code using templates and spec
        code = "# Generated code placeholder"  # Placeholder for now
        
        return {
            'code': code,
            'language': language,
            'framework': framework,
            'type': 'source'
        }
    except Exception as e:
        return {
            'error': str(e),
            'code': '',
            'language': language,
            'framework': framework,
            'type': 'source'
        }

def _generate_test(
    spec: CodeSpec,
    language: str,
    framework: str,
    context: GenerationContext
) -> Dict[str, Any]:
    """
    Generates test code for the specified language and framework using the provided specification.
    
    The function selects an appropriate test template based on the language and framework, formats test components such as fixtures, setup, arrange, act, and assertions, and returns the generated test code along with metadata. If the language or framework is unsupported, an error is returned in the result dictionary.
    
    Args:
        spec: The code specification containing test details such as module, name, scenario, fixtures, setup, arrange, act, and assertions.
        language: The target programming language for the test code.
        framework: The test framework to use (e.g., pytest, unittest, jest, mocha).
        context: Additional context for code generation.
    
    Returns:
        A dictionary containing the generated test code, language, framework, type, and error information if applicable.
    """
    test_templates = {
        'python': {
            'pytest': '''import pytest
from {module} import {name}

{fixtures}

def test_{name}_{scenario}():
    """Test {name} {scenario}"""
    {arrange}
    {act}
    {assert_block}''',
            'unittest': '''import unittest
from {module} import {name}

class Test{name}(unittest.TestCase):
    {setup}
    
    def test_{scenario}(self):
        """Test {name} {scenario}"""
        {arrange}
        {act}
        {assert_block}'''
        },
        'typescript': {
            'jest': '''import { {name} } from '{module}'

describe('{name}', () => {
  {before_each}
  
  test('{scenario}', () => {
    {arrange}
    {act}
    {assert_block}
  })
})''',
            'mocha': '''import { expect } from 'chai'
import { {name} } from '{module}'

describe('{name}', () => {
  {before_each}
  
  it('{scenario}', () => {
    {arrange}
    {act}
    {assert_block}
  })
})'''
        }
    }
    
    try:
        if language not in test_templates:
            raise ValueError(f'Unsupported language: {language}')
            
        if framework not in test_templates[language]:
            framework = list(test_templates[language].keys())[0]
            
        template = test_templates[language][framework]
        
        # Helper functions to format test components
        def _format_fixtures(fixtures: List[str], lang: str) -> str:
            """
            Formats test fixture definitions for the specified language.
            
            Args:
                fixtures: A list of fixture names.
                lang: The programming language for which to format the fixtures.
            
            Returns:
                A string containing formatted fixture definitions, or an empty string if no fixtures are provided or the language is unsupported.
            """
            if not fixtures:
                return ""
                
            if lang == 'python':
                return "\n".join(f"@pytest.fixture\ndef {f}():\n    return {fixtures[f]}" 
                               for f in fixtures)
            return ""
            
        def _format_setup(setup: List[str], lang: str) -> str:
            """
            Formats setup code statements for inclusion in test functions.
            
            Args:
                setup: List of setup statements.
                lang: Target programming language ("python" or "typescript").
            
            Returns:
                A formatted string of setup statements with appropriate indentation for the specified language.
            """
            if not setup:
                return ""
                
            if lang == 'python':
                return "\n    ".join(setup)
            elif lang == 'typescript':
                return "\n  ".join(setup)
            return ""
            
        def _format_arrange(arrange: List[str], lang: str) -> str:
            """
            Formats the arrangement section of a test case for the specified programming language.
            
            Args:
                arrange: List of statements to set up test conditions.
                lang: Target programming language ('python' or 'typescript').
            
            Returns:
                A formatted string representing the arrange block for the test, or a language-appropriate placeholder if empty.
            """
            if not arrange:
                return "pass" if lang == 'python' else ""
                
            if lang == 'python':
                return "\n    ".join(arrange)
            elif lang == 'typescript':
                return "\n    ".join(arrange)
            return ""
            
        def _format_act(act: List[str], lang: str) -> str:
            """
            Formats the action section of a test case for the specified programming language.
            
            Args:
                act: List of action statements to execute in the test.
                lang: Target programming language ('python' or 'typescript').
            
            Returns:
                A formatted string representing the action steps, properly indented for the language.
                Returns 'pass' for Python if no actions are provided, or an empty string for TypeScript.
            """
            if not act:
                return "pass" if lang == 'python' else ""
                
            if lang == 'python':
                return "\n    ".join(act)
            elif lang == 'typescript':
                return "\n    ".join(act)
            return ""
            
        def _format_assertions(assertions: List[str], lang: str) -> str:
            """
            Formats a list of test assertions for the specified programming language.
            
            Args:
                assertions: List of assertion statements as strings.
                lang: Target programming language ('python' or 'typescript').
            
            Returns:
                A formatted string of assertions suitable for inclusion in test code. If no assertions are provided, returns a default passing assertion for the specified language.
            """
            if not assertions:
                return "assert True" if lang == 'python' else "expect(true).toBe(true)"
                
            if lang == 'python':
                return "\n    ".join(assertions)
            elif lang == 'typescript':
                return "\n    ".join(assertions)
            return ""
        
        # Extract test components from spec
        module = spec.module if hasattr(spec, 'module') else spec.get('module', '')
        name = spec.name if hasattr(spec, 'name') else spec.get('name', '')
        scenario = spec.scenario if hasattr(spec, 'scenario') else spec.get('scenario', 'basic')
        fixtures = spec.fixtures if hasattr(spec, 'fixtures') else spec.get('fixtures', [])
        setup = spec.setup if hasattr(spec, 'setup') else spec.get('setup', [])
        arrange = spec.arrange if hasattr(spec, 'arrange') else spec.get('arrange', [])
        act = spec.act if hasattr(spec, 'act') else spec.get('act', [])
        assertions = spec.assertions if hasattr(spec, 'assertions') else spec.get('assertions', [])
        
        # Generate test code using template
        code = template.format(
            module=module,
            name=name,
            scenario=scenario,
            fixtures=_format_fixtures(fixtures, language),
            setup=_format_setup(setup, language),
            arrange=_format_arrange(arrange, language),
            act=_format_act(act, language),
            assert_block=_format_assertions(assertions, language)
        )
        
        return {
            'code': code,
            'language': language,
            'framework': framework,
            'type': 'test'
        }
    except Exception as e:
        return {
            'error': str(e),
            'code': '',
            'language': language,
            'framework': framework,
            'type': 'test'
        }

def _generate_docs(
    spec: Dict[str, Any],
    language: str,
    framework: Optional[str],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generates documentation for code elements using language-specific templates.
    
    Selects and fills a documentation template (Google or NumPy for Python, JSDoc for TypeScript) based on the specified language and framework. Returns a dictionary containing the generated documentation, language, framework, and type. If the language or framework is unsupported, returns an error dictionary.
    """
    doc_templates = {
        'python': {
            'google': '''"""{summary}

{description}

Args:
{args}

Returns:
{returns}

Raises:
{raises}

Examples:
{examples}
"""''',
            'numpy': '''"""{summary}

{description}

Parameters
----------
{parameters}

Returns
-------
{returns}

Raises
------
{raises}

Examples
--------
{examples}
"""'''
        },
        'typescript': {
            'jsdoc': '''/**
 * {summary}
 *
 * {description}
 *
 * @param {parameters}
 * @returns {returns}
 * @throws {throws}
 *
 * @example
 * {examples}
 */'''
        }
    }
    
    if language not in doc_templates:
        return {'error': f'Unsupported language: {language}'}
        
    if not framework:
        framework = list(doc_templates[language].keys())[0]
        
    if framework not in doc_templates[language]:
        return {'error': f'Unsupported doc framework: {framework}'}
        
    template = doc_templates[language][framework]
    
    code = template.format(
        summary=spec.get('summary', ''),
        description=spec.get('description', ''),
        args=_format_doc_args(spec.get('args', []), language, framework),
        parameters=_format_doc_params(spec.get('parameters', []), language, framework),
        returns=_format_doc_returns(spec.get('returns', {}), language, framework),
        raises=_format_doc_raises(spec.get('raises', []), language, framework),
        throws=_format_doc_throws(spec.get('throws', []), language, framework),
        examples=_format_doc_examples(spec.get('examples', []), language, framework)
    )
    
    return {
        'code': code,
        'language': language,
        'framework': framework,
        'type': 'docs'
    }

def _format_params(params: List[Dict[str, Any]], language: str) -> str:
    """Format function/method parameters."""
    if language == 'python':
        return ', '.join([
            f"{p['name']}: {p.get('type', 'Any')}" + 
            (f" = {p['default']}" if 'default' in p else '')
            for p in params
        ])
    elif language == 'typescript':
        return ', '.join([
            f"{p['name']}: {p.get('type', 'any')}" +
            (f" = {p['default']}" if 'default' in p else '')
            for p in params
        ])
    return ''

def _format_type(type_spec: Optional[Dict[str, Any]], language: str) -> str:
    """Format type annotations."""
    if not type_spec:
        return 'Any' if language == 'python' else 'any'
        
    if language == 'python':
        if type_spec.get('kind') == 'union':
            return ' | '.join(type_spec['types'])
        return type_spec.get('name', 'Any')
    elif language == 'typescript':
        if type_spec.get('kind') == 'union':
            return type_spec['types'].join(' | ')
        return type_spec.get('name', 'any')
    return ''

def _format_body(statements: List[str], language: str) -> str:
    """Format code body with proper indentation."""
    if language == 'python':
        return '\n    '.join(statements)
    elif language == 'typescript':
        return '\n  '.join(statements)
    return ''

def _format_methods(methods: List[Dict[str, Any]], language: str) -> str:
    """Format class methods."""
    if not methods:
        return ''
        
    if language == 'python':
        return '\n\n'.join([
            f"def {m['name']}(self{', ' if m.get('params') else ''}{_format_params(m.get('params', []), language)}) -> {_format_type(m.get('return_type'), language)}:\n" +
            f"    \"\"\"{m.get('docstring', '')}\"\"\"\n" +
            f"    {_format_body(m.get('body', []), language)}"
            for m in methods
        ])
    elif language == 'typescript':
        return '\n\n'.join([
            f"{m.get('visibility', '')} {m['name']}({_format_params(m.get('params', []), language)}): {_format_type(m.get('return_type'), language)} " +
            "{\n" +
            f"  {_format_body(m.get('body', []), language)}\n" +
            "}"
            for m in methods
        ])
    return ''

def _format_imports(imports: List[Dict[str, Any]], language: str) -> str:
    """Format import statements."""
    if language == 'python':
        return '\n'.join([
            f"from {i['module']} import {', '.join(i['names'])}"
            if i.get('names') else f"import {i['module']}"
            for i in imports
        ])
    elif language == 'typescript':
        return '\n'.join([
            f"import {{ {', '.join(i['names'])} }} from '{i['module']}';"
            if i.get('names') else f"import {i['module']};"
            for i in imports
        ])
    return ''

# Helper functions for test generation
def _format_fixtures(fixtures: List[Dict[str, Any]], language: str) -> str:
    """Format test fixtures."""
    if language == 'python':
        return '\n\n'.join([
            f"@pytest.fixture\ndef {f['name']}():\n    {_format_body(f['setup'], language)}"
            for f in fixtures
        ])
    return ''

def _format_setup(setup: List[str], language: str) -> str:
    """Format test setup code."""
    if language == 'python':
        return _format_body(setup, language)
    elif language == 'typescript':
        return _format_body(setup, language)
    return ''

def _format_arrange(arrange: List[str], language: str) -> str:
    """Format test arrangement code."""
    return _format_body(arrange, language)

def _format_act(act: List[str], language: str) -> str:
    """Format test action code."""
    return _format_body(act, language)

def _format_assertions(assertions: List[str], language: str) -> str:
    """Format test assertions."""
    return _format_body(assertions, language)

# Helper functions for documentation generation
def _format_doc_args(args: List[Dict[str, Any]], language: str, framework: str) -> str:
    """Format documentation arguments section."""
    if language == 'python':
        if framework == 'google':
            return '\n'.join([
                f"    {a['name']} ({a['type']}): {a['description']}"
                for a in args
            ])
        elif framework == 'numpy':
            return '\n'.join([
                f"{a['name']} : {a['type']}\n    {a['description']}"
                for a in args
            ])
    return ''

def _format_doc_params(params: List[Dict[str, Any]], language: str, framework: str) -> str:
    """Format documentation parameters section."""
    if language == 'typescript':
        return '\n'.join([
            f" * @param {{{p['type']}}} {p['name']} - {p['description']}"
            for p in params
        ])
    return _format_doc_args(params, language, framework)

def _format_doc_returns(returns: Dict[str, Any], language: str, framework: str) -> str:
    """Format documentation returns section."""
    if not returns:
        return ''
        
    if language == 'python':
        if framework == 'google':
            return f"    {returns.get('type')}: {returns.get('description')}"
        elif framework == 'numpy':
            return f"{returns.get('type')}\n    {returns.get('description')}"
    elif language == 'typescript':
        return f" * @returns {{{returns.get('type')}}} {returns.get('description')}"
    return ''

def _format_doc_raises(raises: List[Dict[str, Any]], language: str, framework: str) -> str:
    """Format documentation raises section."""
    if language == 'python':
        if framework == 'google':
            return '\n'.join([
                f"    {r['type']}: {r['description']}"
                for r in raises
            ])
        elif framework == 'numpy':
            return '\n'.join([
                f"{r['type']}\n    {r['description']}"
                for r in raises
            ])
    return ''

def _format_doc_throws(throws: List[Dict[str, Any]], language: str, framework: str) -> str:
    """Format documentation throws section."""
    if language == 'typescript':
        return '\n'.join([
            f" * @throws {{{t['type']}}} {t['description']}"
            for t in throws
        ])
    return ''

def _format_doc_examples(examples: List[str], language: str, framework: str) -> str:
    """Format documentation examples section."""
    if language == 'python':
        if framework == 'google':
            return '\n'.join([f"    >>> {e}" for e in examples])
        elif framework == 'numpy':
            return '\n'.join(examples)
    elif language == 'typescript':
        return '\n * ' + '\n * '.join(examples)
    return '' 