"""
Condition Evaluator for workflow branching.

This module provides a safe and flexible system for evaluating conditions
in workflow steps, without using Python's dangerous eval() function.
Supports variable lookups, comparisons, boolean logic, and simple functions.
"""

import logging
import re
import operator
from typing import Dict, Any, List, Callable, Optional, Tuple, Set
from enum import Enum

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
    
    def __init__(self, message: str, position: int):
        """Initialize a syntax error.
        
        Args:
            message: Error message
            position: Position in the source string
        """
        self.message = message
        self.position = position
        super().__init__(f"{message} at position {position}")

class ConditionEvaluationError(Exception):
    """Exception raised for runtime errors in condition evaluation."""
    
    def __init__(self, message: str):
        """Initialize an evaluation error.
        
        Args:
            message: Error message
        """
        self.message = message
        super().__init__(message)

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
    
    # Available functions
    FUNCTIONS = {
        "exists": lambda x: x is not None,
        "is_empty": lambda x: x is None or (hasattr(x, "__len__") and len(x) == 0),
        "length": lambda x: len(x) if hasattr(x, "__len__") else 0,
        "contains": lambda x, y: y in x if hasattr(x, "__contains__") else False,
    }
    
    def __init__(self, debug_mode: bool = False):
        """Initialize a condition evaluator.
        
        Args:
            debug_mode: Whether to enable debug mode with detailed logging
        """
        self.debug_mode = debug_mode
        self._trace: List[str] = []
        
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
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error validating condition: {str(e)}"
    
    def _tokenize(self, condition: str) -> List[Token]:
        """Tokenize a condition expression.
        
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
            raise ConditionSyntaxError("Unexpected end of expression", len(tokens))
            
        func_token = tokens[pos]
        func_name = func_token.value
        
        if func_name not in self.FUNCTIONS:
            raise ConditionSyntaxError(f"Unknown function: {func_name}", func_token.position)
            
        # Check for opening parenthesis
        pos += 1
        if pos >= len(tokens) or tokens[pos].type != TokenType.LEFT_PAREN:
            raise ConditionSyntaxError(
                f"Expected '(' after function name '{func_name}'",
                func_token.position + len(func_name)
            )
            
        # Parse arguments
        args = []
        pos += 1
        
        # Handle empty argument list
        if pos < len(tokens) and tokens[pos].type == TokenType.RIGHT_PAREN:
            if self.FUNCTIONS[func_name].__code__.co_argcount > 0:
                raise ConditionEvaluationError(
                    f"Function '{func_name}' requires arguments but none were provided"
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
                    len(tokens)
                )
                
            if tokens[pos].type == TokenType.RIGHT_PAREN:
                break
                
            if tokens[pos].type != TokenType.COMMA:
                raise ConditionSyntaxError(
                    f"Expected ',' or ')' in arguments to '{func_name}'",
                    tokens[pos].position
                )
                
            pos += 1
            
        # Check argument count
        expected_arg_count = self.FUNCTIONS[func_name].__code__.co_argcount
        if len(args) != expected_arg_count:
            raise ConditionEvaluationError(
                f"Function '{func_name}' expects {expected_arg_count} arguments but got {len(args)}"
            )
            
        # Call the function
        try:
            result = self.FUNCTIONS[func_name](*args)
            
            if self.debug_mode:
                args_str = ", ".join([str(arg) for arg in args])
                self._trace.append(f"{func_name}({args_str}) -> {result}")
                
            return result, pos + 1
            
        except Exception as e:
            raise ConditionEvaluationError(
                f"Error calling function '{func_name}': {str(e)}"
            )
    
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

# Global evaluator instance
condition_evaluator = ConditionEvaluator()

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
        evaluator = ConditionEvaluator(debug_mode=True)
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