"""
Documentation tools for code analysis and documentation generation.

This module provides tools for:
1. Parsing and validating Python docstrings
2. Analyzing type hints in Python code
3. Generating Markdown documentation
4. Generating OpenAPI documentation
"""
from typing import Dict, Any, List, Optional, Set
import ast
import inspect
from pathlib import Path
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DocstringParser:
    """Parser for Python docstrings with validation and generation capabilities."""
    
    def __init__(self):
        self.docstring_patterns = {
            'google': r'^([A-Za-z_][A-Za-z0-9_]*):[\s\n]+((?:[^\n]+\n?)+)',
            'numpy': r'^([A-Za-z_][A-Za-z0-9_]*)\n[-]+\n((?:[^\n]+\n?)+)',
            'sphinx': r':param ([^:]+): ([^\n]+)',
        }
    
    async def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse all docstrings in a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dict containing parsed docstrings for all functions and classes
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            docstrings = {}
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    docstring = ast.get_docstring(node)
                    if docstring:
                        docstrings[node.name] = self._parse_docstring(docstring)
            
            return docstrings
        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {str(e)}")
            raise
    
    def _parse_docstring(self, docstring: str) -> Dict[str, Any]:
        """Parse a single docstring.
        
        Args:
            docstring: The docstring to parse
            
        Returns:
            Dict containing parsed docstring components
        """
        components = {
            'description': '',
            'args': {},
            'returns': None,
            'raises': [],
            'examples': []
        }
        
        # Extract main description
        parts = docstring.split('\n\n')
        if parts:
            components['description'] = parts[0].strip()
        
        # Parse arguments
        for pattern in self.docstring_patterns.values():
            matches = re.finditer(pattern, docstring, re.MULTILINE)
            for match in matches:
                name, desc = match.groups()
                if name.lower().startswith(('param', 'arg')):
                    param_name = name.split(' ')[-1]
                    components['args'][param_name] = desc.strip()
                elif name.lower().startswith('return'):
                    components['returns'] = desc.strip()
                elif name.lower().startswith('raise'):
                    components['raises'].append(desc.strip())
                elif name.lower() == 'example':
                    components['examples'].append(desc.strip())
        
        return components
    
    async def generate_missing(self, file_path: str) -> Dict[str, str]:
        """Generate missing docstrings based on type hints.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dict mapping function names to generated docstrings
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            generated = {}
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not ast.get_docstring(node):
                    generated[node.name] = self._generate_docstring(node)
            
            return generated
        except Exception as e:
            logger.error(f"Failed to generate docstrings for {file_path}: {str(e)}")
            raise
    
    def _generate_docstring(self, node: ast.FunctionDef) -> str:
        """Generate a docstring for a function based on its type hints."""
        docstring = [f"{node.name} function.\n"]
        
        # Add arguments
        if node.args.args:
            docstring.append("Args:")
            for arg in node.args.args:
                if arg.annotation:
                    arg_type = ast.unparse(arg.annotation)
                    docstring.append(f"    {arg.arg} ({arg_type}): Description")
        
        # Add return type if present
        if node.returns:
            return_type = ast.unparse(node.returns)
            docstring.append("\nReturns:")
            docstring.append(f"    {return_type}: Description")
        
        return "\n".join(docstring)
    
    async def validate(self, file_path: str) -> List[Dict[str, Any]]:
        """Validate docstrings in a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            List of validation issues found
        """
        try:
            docstrings = await self.parse_file(file_path)
            issues = []
            
            for name, parsed in docstrings.items():
                # Check for empty description
                if not parsed['description']:
                    issues.append({
                        'type': 'missing_description',
                        'function': name,
                        'message': 'Missing docstring description'
                    })
                
                # Check for undocumented arguments
                with open(file_path, 'r') as f:
                    content = f.read()
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == name:
                        arg_names = {arg.arg for arg in node.args.args if arg.arg != 'self'}
                        doc_args = set(parsed['args'].keys())
                        missing_args = arg_names - doc_args
                        if missing_args:
                            issues.append({
                                'type': 'missing_args',
                                'function': name,
                                'message': f'Missing documentation for arguments: {missing_args}'
                            })
            
            return issues
        except Exception as e:
            logger.error(f"Failed to validate docstrings in {file_path}: {str(e)}")
            raise

class TypeHintAnalyzer:
    """Analyzer for Python type hints."""
    
    async def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze type hints in a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dict containing analysis of type hints
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            analysis = {
                'functions': {},
                'missing_hints': [],
                'complex_types': [],
                'type_usage': {}
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis['functions'][node.name] = self._analyze_function(node)
            
            return analysis
        except Exception as e:
            logger.error(f"Failed to analyze type hints in {file_path}: {str(e)}")
            raise
    
    def _analyze_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze type hints in a function definition."""
        analysis = {
            'args': {},
            'return_type': None,
            'has_complete_hints': True
        }
        
        # Analyze arguments
        for arg in node.args.args:
            if arg.arg == 'self':
                continue
            if arg.annotation:
                analysis['args'][arg.arg] = ast.unparse(arg.annotation)
            else:
                analysis['has_complete_hints'] = False
        
        # Analyze return type
        if node.returns:
            analysis['return_type'] = ast.unparse(node.returns)
        else:
            analysis['has_complete_hints'] = False
        
        return analysis

class MarkdownGenerator:
    """Generator for Markdown documentation."""
    
    async def generate_docs(self, file_path: str) -> str:
        """Generate Markdown documentation for a Python file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Generated Markdown documentation
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            doc_parts = [
                f"# {Path(file_path).stem}\n",
                f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            ]
            
            # Module docstring
            module_doc = ast.get_docstring(tree)
            if module_doc:
                doc_parts.append("## Overview\n")
                doc_parts.append(f"{module_doc}\n")
            
            # Classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    doc_parts.append(self._generate_class_doc(node))
            
            # Functions
            standalone_funcs = [
                node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
                and not isinstance(node.parent, ast.ClassDef)
            ]
            if standalone_funcs:
                doc_parts.append("## Functions\n")
                for func in standalone_funcs:
                    doc_parts.append(self._generate_method_doc(func))
            
            return "\n".join(doc_parts)
        except Exception as e:
            logger.error(f"Failed to generate Markdown docs for {file_path}: {str(e)}")
            raise
    
    def _generate_class_doc(self, node: ast.ClassDef) -> str:
        """Generate documentation for a class."""
        doc_parts = [f"## Class: {node.name}\n"]
        
        # Class docstring
        class_doc = ast.get_docstring(node)
        if class_doc:
            doc_parts.append(f"{class_doc}\n")
        
        # Methods
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        if methods:
            doc_parts.append("### Methods\n")
            for method in methods:
                doc_parts.append(self._generate_method_doc(method))
        
        return "\n".join(doc_parts)
    
    def _generate_method_doc(self, node: ast.FunctionDef) -> str:
        """Generate documentation for a method or function."""
        doc_parts = [f"#### {node.name}\n"]
        
        # Signature
        args = []
        for arg in node.args.args:
            if arg.arg == 'self':
                continue
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)
        
        signature = f"```python\n{node.name}({', '.join(args)})"
        if node.returns:
            signature += f" -> {ast.unparse(node.returns)}"
        signature += "\n```\n"
        doc_parts.append(signature)
        
        # Docstring
        docstring = ast.get_docstring(node)
        if docstring:
            doc_parts.append(f"{docstring}\n")
        
        return "\n".join(doc_parts)

class OpenAPIGenerator:
    """Generator for OpenAPI documentation."""
    
    async def generate_docs(self, app) -> Dict[str, Any]:
        """Generate OpenAPI documentation for a FastAPI application.
        
        Args:
            app: FastAPI application instance
            
        Returns:
            Dict containing OpenAPI documentation
        """
        try:
            openapi_schema = app.openapi()
            
            # Enhance schema with additional information
            openapi_schema.update({
                'info': {
                    'title': app.title,
                    'version': app.version,
                    'description': app.description,
                    'contact': {
                        'name': 'API Support',
                        'email': 'support@example.com'
                    },
                    'license': {
                        'name': 'MIT',
                        'url': 'https://opensource.org/licenses/MIT'
                    }
                }
            })
            
            return openapi_schema
        except Exception as e:
            logger.error(f"Failed to generate OpenAPI docs: {str(e)}")
            raise
    
    async def validate(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate OpenAPI documentation.
        
        Args:
            schema: OpenAPI schema to validate
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        # Check required fields
        required_fields = ['openapi', 'info', 'paths']
        for field in required_fields:
            if field not in schema:
                issues.append({
                    'type': 'missing_field',
                    'field': field,
                    'message': f'Required field {field} is missing'
                })
        
        # Check info object
        if 'info' in schema:
            info_required = ['title', 'version']
            for field in info_required:
                if field not in schema['info']:
                    issues.append({
                        'type': 'missing_info',
                        'field': field,
                        'message': f'Required info field {field} is missing'
                    })
        
        # Check paths
        if 'paths' in schema:
            for path, methods in schema['paths'].items():
                for method, operation in methods.items():
                    # Check operation ID
                    if 'operationId' not in operation:
                        issues.append({
                            'type': 'missing_operation_id',
                            'path': path,
                            'method': method,
                            'message': 'Operation ID is missing'
                        })
                    
                    # Check responses
                    if 'responses' not in operation:
                        issues.append({
                            'type': 'missing_responses',
                            'path': path,
                            'method': method,
                            'message': 'Responses are missing'
                        })
        
        return issues 