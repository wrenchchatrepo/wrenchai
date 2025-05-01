"""
Condition Evaluator for workflow branching.

This module provides a safe and flexible system for evaluating conditions
in workflow steps, without using Python's dangerous eval() function.
Supports variable lookups, comparisons, boolean logic, and various utility functions
for string, array, type checking, and numeric operations.
"""

import logging
import re
import operator
import functools
from typing import Dict, Any, List, Callable, Optional, Tuple, Set, Union, cast
from enum import Enum
from functools import lru_cache

logger = logging.getLogger(__name__)

class TokenType(Enum):
    """Types of tokens in a condition expression."""
    VARIABLE = "VARIABLE"
    STRING = "STRING"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    OPERATOR = "OPERATOR"
    FUNCTION = "FUNCTION"
    LEFT_PAREN = "LEFT_PAREN"
    RIGHT_PAREN = "RIGHT_PAREN"
    COMMA = "COMMA"

class Token:
    """Token in a condition expression."""
    
    def __init__(self, token_type: TokenType, value: Any, position: int):
        """Initialize a token.
        
        Args:
            token_type: Type of the token
            value: Value of the token
            position: Position in the source string
        """
        self.type = token_type
        self.value = value
        self.position = position
        
    def __str__(self) -> str:
        """Get string representation of the token."""
        return f"{self.type.value}({self.value})"

class ConditionSyntaxError(Exception):
    """Exception raised for syntax errors in condition expressions."""
    
    def __init__(self, message: str, position: int, suggestion: Optional[str] = None):
        """Initialize a syntax error.
        
        Args:
            message: Error message
            position: Position in the source string
            suggestion: Optional suggestion for fixing the error
        """
        self.message = message
        self.position = position
        self.suggestion = suggestion
        error_message = f"{message} at position {position}"
        if suggestion:
            error_message += f"\nSuggestion: {suggestion}"
        super().__init__(error_message)

class ConditionEvaluationError(Exception):
    """Exception raised for runtime errors in condition evaluation."""
    
    def __init__(self, message: str, suggestion: Optional[str] = None):
        """Initialize an evaluation error.
        
        Args:
            message: Error message
            suggestion: Optional suggestion for fixing the error
        """
        self.message = message
        self.suggestion = suggestion
        error_message = message
        if suggestion:
            error_message += f"\nSuggestion: {suggestion}"
        super().__init__(error_message)

class ConditionEvaluator:
    """Safe evaluator for workflow condition expressions."""
    
    # Comparison operators
    COMPARISON_OPS = {
        "==": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
    }
    
    # Boolean operators
    BOOLEAN_OPS = {
        "and": lambda x, y: x and y,
        "or": lambda x, y: x or y,
        "not": lambda x: not x,
    }
    
    # Helper functions for the function implementations
    @staticmethod
    def _safe_str(value: Any) -> str:
        """Safely convert value to string."""
        return str(value) if value is not None else ""
    
    @staticmethod
    def _is_iterable(value: Any) -> bool:
        """Check if value is iterable (list, tuple, etc.)."""
        return hasattr(value, "__iter__") and not isinstance(value, (str, dict))
    
    @staticmethod
    def _safe_number(value: Any) -> Union[int, float, None]:
        """Safely convert value to number."""
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return int(value) if value.isdigit() else float(value)
            except (ValueError, TypeError):
                return None
        return None
    
    # Available functions
    FUNCTIONS = {
        # Existing functions
        "exists": lambda x: x is not None,
        "is_empty": lambda x: x is None or (hasattr(x, "__len__") and len(x) == 0),
        "length": lambda x: len(x) if hasattr(x, "__len__") else 0,
        "contains": lambda x, y: y in x if hasattr(x, "__contains__") else False,
        
        # String functions
        "starts_with": lambda x, y: _safe_str(x).startswith(_safe_str(y)),
        "ends_with": lambda x, y: _safe_str(x).endswith(_safe_str(y)),
        "contains_string": lambda x, y: _safe_str(y) in _safe_str(x),
        "matches_regex": lambda x, y: bool(re.search(_safe_str(y), _safe_str(x))) if re.compile(_safe_str(y)) else False,
        
        # Array functions
        "any_match": lambda arr, func, *args: any(func(item, *args) for item in arr) if _is_iterable(arr) else False,
        "all_match": lambda arr, func, *args: all(func(item, *args) for item in arr) if _is_iterable(arr) else False,
        "has_item": lambda arr, item: item in arr if _is_iterable(arr) else False,
        "count_items": lambda arr: len(arr) if _is_iterable(arr) else 0,
        
        # Type checking functions
        "is_string": lambda x: isinstance(x, str),
        "is_number": lambda x: isinstance(x, (int, float)) or (isinstance(x, str) and x.replace(".", "", 1).isdigit()),
        "is_boolean": lambda x: isinstance(x, bool),
        "is_array": lambda x: _is_iterable(x),
        "is_object": lambda x: isinstance(x, dict),
        
        # Numeric functions
        "is_greater": lambda x, y: _safe_number(x) > _safe_number(y) if _safe_number(x) is not None and _safe_number(y) is not None else False,
        "is_less": lambda x, y: _safe_number(x) < _safe_number(y) if _safe_number(x) is not None and _safe_number(y) is not None else False,
        "sum": lambda arr: sum(_safe_number(x) for x in arr if _safe_number(x) is not None) if _is_iterable(arr) else 0,
        "average": lambda arr: sum(_safe_number(x) for x in arr if _safe_number(x) is not None) / len([x for x in arr if _safe_number(x) is not None]) if _is_iterable(arr) and any(_safe_number(x) is not None for x in arr) else 0,
    }
    
    # Fix references to static methods in function definitions
    FUNCTIONS["starts_with"] = lambda x, y: ConditionEvaluator._safe_str(x).startswith(ConditionEvaluator._safe_str(y))
    FUNCTIONS["ends_with"] = lambda x, y: ConditionEvaluator._safe_str(x).endswith(ConditionEvaluator._safe_str(y))
    FUNCTIONS["contains_string"] = lambda x, y: ConditionEvaluator._safe_str(y) in ConditionEvaluator._safe_str(x)
    FUNCTIONS["matches_regex"] = lambda x, y: bool(re.search(ConditionEvaluator._safe_str(y), ConditionEvaluator._safe_str(x))) if re.compile(ConditionEvaluator._safe_str(y)) else False
    FUNCTIONS["any_match"] = lambda arr, func, *args: any(func(item, *args) for item in arr) if ConditionEvaluator._is_iterable(arr) else False
    FUNCTIONS["all_match"] = lambda arr, func, *args: all(func(item, *args) for item in arr) if ConditionEvaluator._is_iterable(arr) else False
    FUNCTIONS["has_item"] = lambda arr, item: item in arr if ConditionEvaluator._is_iterable(arr) else False
    FUNCTIONS["count_items"] = lambda arr: len(arr) if ConditionEvaluator._is_iterable(arr) else 0
    FUNCTIONS["is_array"] = lambda x: ConditionEvaluator._is_iterable(x)
    FUNCTIONS["is_greater"] = lambda x, y: ConditionEvaluator._safe_number(x) > ConditionEvaluator._safe_number(y) if ConditionEvaluator._safe_number(x) is not None and ConditionEvaluator._safe_number(y) is not None else False
    FUNCTIONS["is_less"] = lambda x, y: ConditionEvaluator._safe_number(x) < ConditionEvaluator._safe_number(y) if ConditionEvaluator._safe_number(x) is not None and ConditionEvaluator._safe_number(y) is not None else False
    FUNCTIONS["sum"] = lambda arr: sum(ConditionEvaluator._safe_number(x) for x in arr if ConditionEvaluator._safe_number(x) is not None) if ConditionEvaluator._is_iterable(arr) else 0
    FUNCTIONS["average"] = lambda arr: sum(ConditionEvaluator._safe_number(x) for x in arr if ConditionEvaluator._safe_number(x) is not None) / len([x for x in arr if ConditionEvaluator._safe_number(x) is not None]) if ConditionEvaluator._is_iterable(arr) and any(ConditionEvaluator._safe_number(x) is not None for x in arr) else 0
    
    # Function help information for error suggestions
    FUNCTION_HELP = {
        "exists": "Check if a value exists (is not None). Usage: exists(variable)",
        "is_empty": "Check if a value is empty. Usage: is_empty(variable)",
        "length": "Get the length of a string, array, or object. Usage: length(variable)",
        "contains": "Check if a value contains another value. Usage: contains(array_or_string, value)",
        "starts_with": "Check if a string starts with another string. Usage: starts_with(string, prefix)",
        "ends_with": "Check if a string ends with another string. Usage: ends_with(string, suffix)",
        "contains_string": "Check if a string contains another string. Usage: contains_string(string, substring)",
        "matches_regex": "Check if a string matches a regex pattern. Usage: matches_regex(string, pattern)",
        "any_match": "Check if any item in an array matches a condition. Usage: any_match(array, function, *args)",
        "all_match": "Check if all items in an array match a condition. Usage: all_match(array, function, *args)",
        "has_item": "Check if an array has a specific item. Usage: has_item(array, item)",
        "count_items": "Count the number of items in an array. Usage: count_items(array)",
        "is_string": "Check if a value is a string. Usage: is_string(value)",
        "is_number": "Check if a value is a number. Usage: is_number(value)",
        "is_boolean": "Check if a value is a boolean. Usage: is_boolean(value)",
        "is_array": "Check if a value is an array. Usage: is_array(value)",
        "is_object": "Check if a value is an object. Usage: is_object(value)",
        "is_greater": "Check if a number is greater than another. Usage: is_greater(value1, value2)",
        "is_less": "Check if a number is less than another. Usage: is_less(value1, value2)",
        "sum": "Calculate the sum of numbers in an array. Usage: sum(array)",
        "average": "Calculate the average of numbers in an array. Usage: average(array)",
    }
    
    # Operator help information for error suggestions
    OPERATOR_HELP = {
        "==": "Equal comparison operator. Usage: value1 == value2",
        "!=": "Not equal comparison operator. Usage: value1 != value2",
        ">": "Greater than comparison operator. Usage: value1 > value2",
        "<": "Less than comparison operator. Usage: value1 < value2",
        ">=": "Greater than or equal comparison operator. Usage: value1 >= value2",
        "<=": "Less than or equal comparison operator. Usage: value1 <= value2",
        "and": "Logical AND operator. Usage: condition1 and condition2",
        "or": "Logical OR operator. Usage: condition1 or condition2",
        "not": "Logical NOT operator. Usage: not condition",
    }
    
    def __init__(self, debug_mode: bool = False, use_caching: bool = True):
        """Initialize a condition evaluator.
        
        Args:
            debug_mode: Whether to enable debug mode with detailed logging
            use_caching: Whether to enable caching for tokenized conditions
        """
        self.debug_mode = debug_mode
        self.use_caching = use_caching
        self._trace: List[str] = []
        # Tokenizer cache is implemented using lru_cache on the method
        
    def evaluate(self, condition: str, variables: Dict[str, Any]) -> bool:
        """Evaluate a condition expression.
        
        Args:
            condition: Condition expression to evaluate
            variables: Dictionary of variables available in the condition
            
        Returns:
            Boolean result of the condition evaluation
            
        Raises:
            ConditionSyntaxError: If the condition has syntax errors
            ConditionEvaluationError: If evaluation fails
        """
        self._trace = []
        
        # Handle edge cases
        if not condition or condition.strip() == "":
            return True  # Empty condition is always true
        
        try:
            # Tokenize the condition
            tokens = self._tokenize(condition)
            
            # Parse and evaluate the tokens
            result = self._parse_and_evaluate(tokens, variables)
            
            # Convert the result to boolean
            if not isinstance(result, bool):
                result = bool(result)
                
            if self.debug_mode:
                logger.debug(f"Evaluated condition '{condition}' to {result}")
                logger.debug(f"Trace: {', '.join(self._trace)}")
                
            return result
            
        except ConditionSyntaxError as e:
            # Add more context to the error message if needed
            if not e.suggestion:
                # Try to provide a more helpful suggestion
                suggestion = self._get_error_suggestion(condition, e.position)
                if suggestion:
                    e.suggestion = suggestion
            logger.error(f"Syntax error evaluating condition '{condition}': {e}")
            raise
            
        except ConditionEvaluationError as e:
            logger.error(f"Evaluation error for condition '{condition}': {e}")
            raise
            
        except Exception as e:
            # Catch any other exceptions and wrap them
            error_msg = f"Unexpected error evaluating condition: {str(e)}"
            logger.error(f"{error_msg} for condition '{condition}'")
            raise ConditionEvaluationError(error_msg, "This may be a bug in the condition evaluator. Check the condition syntax.")
    
    def _get_error_suggestion(self, condition: str, position: int) -> Optional[str]:
        """Generate suggestions for syntax errors.
        
        Args:
            condition: Original condition string
            position: Position of the error
            
        Returns:
            Suggestion string or None if no suggestion can be made
        """
        # Extract the context around the error
        start = max(0, position - 10)
        end = min(len(condition), position + 10)
        context = condition[start:end]
        
        # Common error cases
        if '==' not in condition and '=' in condition:
            return "Use '==' for equality comparison, not '='"
            
        if ')' in condition and '(' not in condition:
            return "Missing opening parenthesis '('"
            
        if '(' in condition and ')' not in condition:
            return "Missing closing parenthesis ')'"
            
        if position > 0 and condition[position-1] in "><!=":
            return "Comparison operators should be '==', '!=', '>', '<', '>=', or '<='"
            
        # Look for unclosed quotes
        quotes = {"'": 0, '"': 0}
        for char in condition[:position]:
            if char in quotes:
                quotes[char] += 1
                
        for q, count in quotes.items():
            if count % 2 != 0:
                return f"Unclosed string literal. Add a matching {q} quote."
                
        # Check for common function names
        tokens = condition[:position].split()
        if tokens:
            last_word = tokens[-1]
            similar_functions = []
            for func in self.FUNCTIONS:
                if func.startswith(last_word[:2]) or self._levenshtein_distance(func, last_word) <= 2:
                    similar_functions.append(func)
                    
            if similar_functions:
                return f"Did you mean one of these functions? {', '.join(similar_functions)}"
                
        return None
    
    def validate_syntax(self, condition: str) -> Tuple[bool, Optional[str]]:
        """Validate the syntax of a condition expression.
        
        Args:
            condition: Condition expression to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not condition or condition.strip() == "":
            return True, None  # Empty condition is valid
            
        try:
            # Tokenize the condition
            tokens = self._tokenize(condition)
            
            # Check basic structural validity
            self._check_token_structure(tokens)
            
            return True, None
            
        except ConditionSyntaxError as e:
            # Add suggestions if not already present
            if not e.suggestion:
                suggestion = self._get_error_suggestion(condition, e.position)
                if suggestion:
                    return False, f"{str(e)}\nSuggestion: {suggestion}"
            return False, str(e)
            
        except Exception as e:
            return False, f"Unexpected error validating condition: {str(e)}"
    
    # Cache for tokenizer to improve performance
    @lru_cache(maxsize=128)
    def _tokenize_cached(self, condition: str) -> List[Token]:
        """Cached version of tokenize for better performance.
        
        Args:
            condition: Condition expression to tokenize
            
        Returns:
            List of tokens
            
        Raises:
            ConditionSyntaxError: If tokenization fails
        """
        return self._tokenize_impl(condition)
    
    def _tokenize(self, condition: str) -> List[Token]:
        """Tokenize a condition expression, with optional caching.
        
        Args:
            condition: Condition expression to tokenize
            
        Returns:
            List of tokens
            
        Raises:
            ConditionSyntaxError: If tokenization fails
        """
        if self.use_caching:
            return self._tokenize_cached(condition)
        else:
            return self._tokenize_impl(condition)
    
    def _tokenize_impl(self, condition: str) -> List[Token]:
        """Implementation of tokenizing a condition expression.
        
        Args:
            condition: Condition expression to tokenize
            
        Returns:
            List of tokens
            
        Raises:
            ConditionSyntaxError: If tokenization fails
        """
        tokens = []
        position = 0
        
        # Pattern for variable names (must start with a letter or underscore)
        variable_pattern = r'[a-zA-Z_][a-zA-Z0-9_]*'
        
        # Pattern for operators
        operator_pattern = r'==|!=|>=|<=|>|<|and|or|not'
        
        # Pattern for numbers
        number_pattern = r'-?\d+(\.\d+)?'
        
        # Combined pattern for tokenizing
        token_pattern = f'({variable_pattern})|({operator_pattern})|({number_pattern})|("[^"]*")|' + \
                       r'(\'[^\']*\')|(\()|(\))|(\,)'
        
        token_regex = re.compile(token_pattern)
        
        for match in token_regex.finditer(condition):
            matched_str = match.group(0)
            pos = match.start()
            
            if match.group(1):  # Variable or function or boolean
                if matched_str == "true":
                    tokens.append(Token(TokenType.BOOLEAN, True, pos))
                elif matched_str == "false":
                    tokens.append(Token(TokenType.BOOLEAN, False, pos))
                elif matched_str in self.BOOLEAN_OPS:
                    tokens.append(Token(TokenType.OPERATOR, matched_str, pos))
                elif matched_str in self.FUNCTIONS:
                    tokens.append(Token(TokenType.FUNCTION, matched_str, pos))
                else:
                    tokens.append(Token(TokenType.VARIABLE, matched_str, pos))
                    
            elif match.group(2):  # Operator
                tokens.append(Token(TokenType.OPERATOR, matched_str, pos))
                
            elif match.group(3):  # Number
                if "." in matched_str:
                    tokens.append(Token(TokenType.NUMBER, float(matched_str), pos))
                else:
                    tokens.append(Token(TokenType.NUMBER, int(matched_str), pos))
                    
            elif match.group(4) or match.group(5):  # String
                # Remove the quotes from the string
                string_value = matched_str[1:-1]
                tokens.append(Token(TokenType.STRING, string_value, pos))
                
            elif match.group(6):  # Left parenthesis
                tokens.append(Token(TokenType.LEFT_PAREN, "(", pos))
                
            elif match.group(7):  # Right parenthesis
                tokens.append(Token(TokenType.RIGHT_PAREN, ")", pos))
                
            elif match.group(8):  # Comma
                tokens.append(Token(TokenType.COMMA, ",", pos))
                
            position = match.end()
            
        # Check for untokenized parts of the condition
        condition_no_whitespace = condition.replace(" ", "").replace("\t", "")
        tokens_str = "".join([
            f"({t.value})" if t.type in [TokenType.VARIABLE, TokenType.FUNCTION, TokenType.OPERATOR] else
            f"{t.value}" if t.type in [TokenType.LEFT_PAREN, TokenType.RIGHT_PAREN, TokenType.COMMA] else
            f'"{t.value}"' if t.type == TokenType.STRING else
            f"{t.value}" 
            for t in tokens
        ])
        
        if tokens_str != condition_no_whitespace and condition_no_whitespace:
            unexplained_part = "".join([c for c in condition_no_whitespace if c not in tokens_str])
            raise ConditionSyntaxError(
                f"Unexpected token(s) in condition: '{unexplained_part}'",
                condition_no_whitespace.find(unexplained_part)
            )
            
        return tokens
    
    def _check_token_structure(self, tokens: List[Token]) -> None:
        """Check the basic structural validity of tokens.
        
        Args:
            tokens: List of tokens to check
            
        Raises:
            ConditionSyntaxError: If the structure is invalid
        """
        # Check parenthesis matching
        paren_count = 0
        for token in tokens:
            if token.type == TokenType.LEFT_PAREN:
                paren_count += 1
            elif token.type == TokenType.RIGHT_PAREN:
                paren_count -= 1
                
            if paren_count < 0:
                raise ConditionSyntaxError("Unmatched closing parenthesis", token.position)
                
        if paren_count > 0:
            raise ConditionSyntaxError("Unmatched opening parenthesis", tokens[-1].position + 1)
            
        # Check for function calls with missing parenthesis
        for i, token in enumerate(tokens):
            if token.type == TokenType.FUNCTION:
                if i + 1 >= len(tokens) or tokens[i + 1].type != TokenType.LEFT_PAREN:
                    raise ConditionSyntaxError(
                        f"Function '{token.value}' must be followed by '('",
                        token.position + len(str(token.value))
                    )
    
    def _parse_and_evaluate(self, tokens: List[Token], variables: Dict[str, Any]) -> Any:
        """Parse and evaluate a list of tokens.
        
        Args:
            tokens: List of tokens to evaluate
            variables: Dictionary of variables available in the condition
            
        Returns:
            Result of the evaluation
            
        Raises:
            ConditionSyntaxError: If the syntax is invalid
            ConditionEvaluationError: If evaluation fails
        """
        # Simple recursive descent parser for the expression
        return self._parse_expression(tokens, 0, variables)[0]
    
    def _parse_expression(
        self, tokens: List[Token], pos: int, variables: Dict[str, Any]
    ) -> Tuple[Any, int]:
        """Parse and evaluate an expression.
        
        Args:
            tokens: List of tokens to evaluate
            pos: Current position in the token list
            variables: Dictionary of variables available in the condition
            
        Returns:
            Tuple of (result, new_position)
            
        Raises:
            ConditionSyntaxError: If the syntax is invalid
            ConditionEvaluationError: If evaluation fails
        """
        if pos >= len(tokens):
            raise ConditionSyntaxError("Unexpected end of expression", len(tokens))
        
        # Parse the first term
        left, pos = self._parse_term(tokens, pos, variables)
        
        # Look for operators
        while pos < len(tokens) and tokens[pos].type == TokenType.OPERATOR:
            op = tokens[pos].value
            
            # Handle 'not' operator (unary)
            if op == "not":
                right, pos = self._parse_term(tokens, pos + 1, variables)
                left = self.BOOLEAN_OPS[op](right)
                continue
            
            # Binary operators
            pos += 1
            right, pos = self._parse_term(tokens, pos, variables)
            
            if op in self.COMPARISON_OPS:
                left = self.COMPARISON_OPS[op](left, right)
            elif op in self.BOOLEAN_OPS:
                left = self.BOOLEAN_OPS[op](left, right)
            else:
                raise ConditionSyntaxError(f"Unknown operator: {op}", tokens[pos - 1].position)
                
            if self.debug_mode:
                self._trace.append(f"{op}({left}, {right}) -> {left}")
        
        return left, pos
    
    def _parse_term(
        self, tokens: List[Token], pos: int, variables: Dict[str, Any]
    ) -> Tuple[Any, int]:
        """Parse and evaluate a term.
        
        Args:
            tokens: List of tokens to evaluate
            pos: Current position in the token list
            variables: Dictionary of variables available in the condition
            
        Returns:
            Tuple of (result, new_position)
            
        Raises:
            ConditionSyntaxError: If the syntax is invalid
            ConditionEvaluationError: If evaluation fails
        """
        if pos >= len(tokens):
            raise ConditionSyntaxError("Unexpected end of expression", len(tokens))
            
        token = tokens[pos]
        
        # Handle literals
        if token.type in [TokenType.NUMBER, TokenType.STRING, TokenType.BOOLEAN]:
            return token.value, pos + 1
            
        # Handle variable
        elif token.type == TokenType.VARIABLE:
            var_name = token.value
            if var_name not in variables:
                if self.debug_mode:
                    self._trace.append(f"Variable '{var_name}' not found, using None")
                return None, pos + 1
                
            var_value = variables[var_name]
            if self.debug_mode:
                self._trace.append(f"Variable '{var_name}' = {var_value}")
                
            return var_value, pos + 1
            
        # Handle parenthesized expression
        elif token.type == TokenType.LEFT_PAREN:
            result, pos = self._parse_expression(tokens, pos + 1, variables)
            
            if pos >= len(tokens) or tokens[pos].type != TokenType.RIGHT_PAREN:
                raise ConditionSyntaxError("Expected closing parenthesis", pos)
                
            return result, pos + 1
            
        # Handle function call
        elif token.type == TokenType.FUNCTION:
            return self._parse_function_call(tokens, pos, variables)
            
        else:
            raise ConditionSyntaxError(
                f"Unexpected token: {token.type.value}({token.value})",
                token.position
            )
    
    def _parse_function_call(
        self, tokens: List[Token], pos: int, variables: Dict[str, Any]
    ) -> Tuple[Any, int]:
        """Parse and evaluate a function call.
        
        Args:
            tokens: List of tokens to evaluate
            pos: Current position in the token list
            variables: Dictionary of variables available in the condition
            
        Returns:
            Tuple of (result, new_position)
            
        Raises:
            ConditionSyntaxError: If the syntax is invalid
            ConditionEvaluationError: If evaluation fails
        """
        if pos >= len(tokens):
            raise ConditionSyntaxError(
                "Unexpected end of expression", 
                len(tokens),
                "Ensure the condition is complete and properly terminated."
            )
            
        func_token = tokens[pos]
        func_name = func_token.value
        
        if func_name not in self.FUNCTIONS:
            # Find similar function names for suggestions
            suggestion = None
            similar_funcs = [f for f in self.FUNCTIONS.keys() if f.startswith(func_name[:2]) or self._levenshtein_distance(f, func_name) <= 2]
            if similar_funcs:
                similar_funcs_str = ", ".join(similar_funcs)
                suggestion = f"Did you mean one of these functions? {similar_funcs_str}"
            elif len(self.FUNCTIONS) <= 10:
                # If there aren't too many functions, list them all
                all_funcs = ", ".join(sorted(self.FUNCTIONS.keys()))
                suggestion = f"Available functions are: {all_funcs}"
            else:
                suggestion = f"Use one of the available functions. Some common ones are: exists, is_empty, length, contains"
                
            raise ConditionSyntaxError(
                f"Unknown function: {func_name}", 
                func_token.position,
                suggestion
            )
            
        # Check for opening parenthesis
        pos += 1
        if pos >= len(tokens) or tokens[pos].type != TokenType.LEFT_PAREN:
            raise ConditionSyntaxError(
                f"Expected '(' after function name '{func_name}'",
                func_token.position + len(func_name),
                f"Function calls require parentheses. Use: {func_name}(...)"
            )
            
        # Parse arguments
        args = []
        pos += 1
        
        # Handle empty argument list
        if pos < len(tokens) and tokens[pos].type == TokenType.RIGHT_PAREN:
            expected_arg_count = self.FUNCTIONS[func_name].__code__.co_argcount
            if expected_arg_count > 0:
                # Include help information about the function
                help_text = self.FUNCTION_HELP.get(func_name, "")
                raise ConditionEvaluationError(
                    f"Function '{func_name}' requires {expected_arg_count} arguments but none were provided",
                    f"Function usage: {help_text}"
                )
                
            result = self.FUNCTIONS[func_name]()
            return result, pos + 1
            
        # Parse arguments
        while True:
            arg, pos = self._parse_expression(tokens, pos, variables)
            args.append(arg)
            
            if pos >= len(tokens):
                raise ConditionSyntaxError(
                    f"Unexpected end of expression in arguments to '{func_name}'",
                    len(tokens),
                    "Ensure all parentheses are properly closed."
                )
                
            if tokens[pos].type == TokenType.RIGHT_PAREN:
                break
                
            if tokens[pos].type != TokenType.COMMA:
                raise ConditionSyntaxError(
                    f"Expected ',' or ')' in arguments to '{func_name}'",
                    tokens[pos].position,
                    f"Use commas to separate function arguments: {func_name}(arg1, arg2, ...)"
                )
                
            pos += 1
            
        # Check argument count
        expected_arg_count = self.FUNCTIONS[func_name].__code__.co_argcount
        if len(args) != expected_arg_count:
            # Include help information about the function
            help_text = self.FUNCTION_HELP.get(func_name, "")
            raise ConditionEvaluationError(
                f"Function '{func_name}' expects {expected_arg_count} arguments but got {len(args)}",
                f"Function usage: {help_text}"
            )
            
        # Call the function
        try:
            result = self.FUNCTIONS[func_name](*args)
            
            if self.debug_mode:
                args_str = ", ".join([str(arg) for arg in args])
                self._trace.append(f"{func_name}({args_str}) -> {result}")
                
            return result, pos + 1
            
        except Exception as e:
            # Include help information about the function
            help_text = self.FUNCTION_HELP.get(func_name, "")
            raise ConditionEvaluationError(
                f"Error calling function '{func_name}': {str(e)}",
                f"Check argument types. Function usage: {help_text}"
            )
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate the Levenshtein distance between two strings.
        
        This is used for suggesting similar function names.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Edit distance between the strings
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
            
        if len(s2) == 0:
            return len(s1)
            
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
            
        return previous_row[-1]
    
    def get_trace(self) -> List[str]:
        """Get the evaluation trace.
        
        Returns:
            List of trace entries
        """
        return self._trace
    
    def get_referenced_variables(self, condition: str) -> Set[str]:
        """Get the variables referenced in a condition.
        
        Args:
            condition: Condition to analyze
            
        Returns:
            Set of variable names
            
        Raises:
            ConditionSyntaxError: If the condition has syntax errors
        """
        if not condition or condition.strip() == "":
            return set()
            
        # Tokenize the condition
        tokens = self._tokenize(condition)
        
        # Find all variable tokens
        variables = set()
        for token in tokens:
            if token.type == TokenType.VARIABLE:
                variables.add(token.value)
                
        return variables

# Global evaluator instance with caching enabled
condition_evaluator = ConditionEvaluator(use_caching=True)

def evaluate_condition(condition: str, variables: Dict[str, Any], debug: bool = False) -> bool:
    """Evaluate a condition with the given variables.
    
    Args:
        condition: Condition expression to evaluate
        variables: Dictionary of variables available in the condition
        debug: Whether to enable debug mode
        
    Returns:
        Boolean result of the condition evaluation
        
    Raises:
        ConditionSyntaxError: If the condition has syntax errors
        ConditionEvaluationError: If evaluation fails
    """
    if debug:
        evaluator = ConditionEvaluator(debug_mode=True, use_caching=True)
        result = evaluator.evaluate(condition, variables)
        return result
    else:
        return condition_evaluator.evaluate(condition, variables)

def validate_condition(condition: str) -> Tuple[bool, Optional[str]]:
    """Validate a condition's syntax.
    
    Args:
        condition: Condition expression to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    return condition_evaluator.validate_syntax(condition)

def get_function_help(function_name: Optional[str] = None) -> Dict[str, str]:
    """Get help information for available condition functions.
    
    Args:
        function_name: Optional name of a specific function to get help for
        
    Returns:
        Dictionary of function help information
    """
    if function_name:
        if function_name in ConditionEvaluator.FUNCTION_HELP:
            return {function_name: ConditionEvaluator.FUNCTION_HELP[function_name]}
        else:
            return {}
    else:
        return ConditionEvaluator.FUNCTION_HELP

def get_condition_variables(condition: str) -> Set[str]:
    """Get the variables referenced in a condition.
    
    Args:
        condition: Condition to analyze
        
    Returns:
        Set of variable names
        
    Raises:
        ConditionSyntaxError: If the condition has syntax errors
    """
    return condition_evaluator.get_referenced_variables(condition)

def analyze_playbook_conditions(playbook_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze all conditions in a playbook.
    
    Args:
        playbook_dict: Playbook dictionary
        
    Returns:
        Dictionary with analysis results
    """
    all_conditions = []
    all_variables = set()
    analysis = {
        "condition_count": 0,
        "variables": [],
        "conditions": [],
        "errors": []
    }
    
    # Extract conditions from process steps
    for step in playbook_dict.get("steps", []):
        step_id = step.get("step_id", "unknown")
        
        # Process steps
        if step.get("type") == "process" and "operations" in step:
            for i, op in enumerate(step["operations"]):
                if "condition" in op and op["condition"]:
                    condition = op["condition"]
                    all_conditions.append({
                        "step_id": step_id,
                        "type": "process",
                        "condition": condition,
                        "index": i
                    })
                    
                    # Validate condition
                    try:
                        valid, error = validate_condition(condition)
                        if not valid:
                            analysis["errors"].append({
                                "step_id": step_id,
                                "condition": condition,
                                "error": error
                            })
                        else:
                            variables = get_condition_variables(condition)
                            all_variables.update(variables)
                    except Exception as e:
                        analysis["errors"].append({
                            "step_id": step_id,
                            "condition": condition,
                            "error": str(e)
                        })
        
        # Handoff steps
        if step.get("type") == "handoff" and "handoff_conditions" in step:
            for i, handoff in enumerate(step["handoff_conditions"]):
                if "condition" in handoff:
                    condition = handoff["condition"]
                    all_conditions.append({
                        "step_id": step_id,
                        "type": "handoff",
                        "condition": condition,
                        "index": i
                    })
                    
                    # Validate condition
                    try:
                        valid, error = validate_condition(condition)
                        if not valid:
                            analysis["errors"].append({
                                "step_id": step_id,
                                "condition": condition,
                                "error": error
                            })
                        else:
                            variables = get_condition_variables(condition)
                            all_variables.update(variables)
                    except Exception as e:
                        analysis["errors"].append({
                            "step_id": step_id,
                            "condition": condition,
                            "error": str(e)
                        })
        
        # Partner feedback loops
        if step.get("type") == "partner_feedback_loop" and "termination_condition" in step:
            condition = step["termination_condition"]
            if condition:
                all_conditions.append({
                    "step_id": step_id,
                    "type": "partner_feedback_loop",
                    "condition": condition
                })
                
                # Validate condition
                try:
                    valid, error = validate_condition(condition)
                    if not valid:
                        analysis["errors"].append({
                            "step_id": step_id,
                            "condition": condition,
                            "error": error
                        })
                    else:
                        variables = get_condition_variables(condition)
                        all_variables.update(variables)
                except Exception as e:
                    analysis["errors"].append({
                        "step_id": step_id,
                        "condition": condition,
                        "error": str(e)
                    })
    
    analysis["condition_count"] = len(all_conditions)
    analysis["variables"] = sorted(list(all_variables))
    analysis["conditions"] = all_conditions
    
    return analysis