# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import json
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

def generate(
    spec: Dict[str, Any],
    language: str,
    framework: str = '',
    output_type: str = 'source',
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate code based on the provided specification.
    
    Args:
        spec: Dictionary containing the code generation specification
        language: Target programming language (python/typescript)
        framework: Optional framework to use (e.g. pytest, jest)
        output_type: Type of output (source/test/docs)
        context: Optional context information
        
    Returns:
        Dictionary containing:
        - code: The generated code as a string
        - language: The target language
        - framework: The framework used (if any)
        - type: The type of output generated
        - error: Error message if generation failed
    """
    if not context:
        context = {}
        
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
        return _generate_code(spec, language, framework, context)
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

def _generate_code(
    spec: Dict[str, Any],
    language: str,
    framework: Optional[str],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate source code."""
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
    
    if language not in code_templates:
        return {'error': f'Unsupported language: {language}'}
        
    templates = code_templates[language]
    
    # Generate code based on spec type
    if spec.get('type') == 'class':
        code = templates['class'].format(
            name=spec['name'],
            docstring=spec.get('docstring', ''),
            params=_format_params(spec.get('params', []), language),
            init_body=_format_body(spec.get('init_body', []), language),
            methods=_format_methods(spec.get('methods', []), language)
        )
    elif spec.get('type') == 'function':
        code = templates['function'].format(
            name=spec['name'],
            params=_format_params(spec.get('params', []), language),
            return_type=_format_type(spec.get('return_type'), language),
            docstring=spec.get('docstring', ''),
            body=_format_body(spec.get('body', []), language)
        )
    elif spec.get('type') == 'module':
        code = templates['module'].format(
            module_docstring=spec.get('docstring', ''),
            imports=_format_imports(spec.get('imports', []), language),
            code=spec.get('code', '')
        )
    else:
        return {'error': f'Unsupported spec type: {spec.get("type")}'}
        
    return {
        'code': code,
        'language': language,
        'framework': framework,
        'type': spec.get('type')
    }

def _generate_test(
    spec: Dict[str, Any],
    language: str,
    framework: Optional[str],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate test code."""
    test_templates = {
        'python': {
            'pytest': '''import pytest
from {module} import {name}

{fixtures}

def test_{name}_{scenario}():
    """Test {description}"""
    {arrange}
    {act}
    {assert_block}''',
            'unittest': '''import unittest
from {module} import {name}

class Test{name}(unittest.TestCase):
    {setup}
    
    def test_{scenario}(self):
        """Test {description}"""
        {arrange}
        {act}
        {assert_block}'''
        },
        'typescript': {
            'jest': '''import { {name} } from '{module}';

describe('{name}', () => {
  {setup}
  
  test('{description}', () => {
    {arrange}
    {act}
    {assert_block}
  });
});'''
        }
    }
    
    if language not in test_templates:
        return {'error': f'Unsupported language: {language}'}
        
    if not framework:
        framework = list(test_templates[language].keys())[0]
        
    if framework not in test_templates[language]:
        return {'error': f'Unsupported test framework: {framework}'}
        
    template = test_templates[language][framework]
    
    code = template.format(
        module=spec['module'],
        name=spec['name'],
        description=spec.get('description', ''),
        scenario=spec.get('scenario', 'basic'),
        fixtures=_format_fixtures(spec.get('fixtures', []), language),
        setup=_format_setup(spec.get('setup', []), language),
        arrange=_format_arrange(spec.get('arrange', []), language),
        act=_format_act(spec.get('act', []), language),
        assert_block=_format_assertions(spec.get('assertions', []), language)
    )
    
    return {
        'code': code,
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
    """Generate documentation."""
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