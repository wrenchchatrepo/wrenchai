"""
Command-line tool for validating and analyzing conditions in playbooks.

This tool helps playbook authors verify condition syntax and find
potential issues like missing variables or logic errors.
"""

import argparse
import json
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

# Add parent directory to path for imports
parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.condition_evaluator import (
    validate_condition, 
    get_condition_variables,
    analyze_playbook_conditions,
    evaluate_condition
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_condition_report(analysis: Dict[str, Any]) -> None:
    """Print a report of playbook conditions.
    
    Args:
        analysis: Condition analysis dictionary
    """
    print("\n=== Playbook Condition Analysis ===\n")
    
    print(f"Total conditions: {analysis['condition_count']}")
    print(f"Variables used: {', '.join(analysis['variables'])}")
    
    if analysis['errors']:
        print("\nErrors found:")
        for error in analysis['errors']:
            print(f"  - Step {error['step_id']}: {error['condition']} - {error['error']}")
    else:
        print("\nNo syntax errors found in conditions.")
    
    print("\nConditions by step:")
    for condition in analysis['conditions']:
        step_id = condition['step_id']
        condition_str = condition['condition']
        condition_type = condition['type']
        
        if 'index' in condition:
            print(f"  - {step_id} [{condition_type}][{condition['index']}]: {condition_str}")
        else:
            print(f"  - {step_id} [{condition_type}]: {condition_str}")

def test_condition(condition: str, variables: Dict[str, Any]) -> None:
    """Test a condition with the given variables.
    
    Args:
        condition: Condition to test
        variables: Variables to use in evaluation
    """
    print(f"\nTesting condition: {condition}")
    print(f"With variables: {json.dumps(variables, indent=2)}")
    
    # Validate syntax
    valid, error = validate_condition(condition)
    if not valid:
        print(f"Syntax error: {error}")
        return
    
    # Get referenced variables
    referenced_vars = get_condition_variables(condition)
    print(f"Referenced variables: {', '.join(referenced_vars)}")
    
    # Check for missing variables
    missing_vars = [var for var in referenced_vars if var not in variables]
    if missing_vars:
        print(f"Warning: Missing variables: {', '.join(missing_vars)}")
    
    # Evaluate condition
    try:
        result = evaluate_condition(condition, variables, debug=True)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Evaluation error: {str(e)}")

def main():
    """Main entry point for the condition validator tool."""
    parser = argparse.ArgumentParser(
        description="Validate and analyze conditions in WrenchAI playbooks."
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Analyze playbook subcommand
    analyze_parser = subparsers.add_parser("analyze", help="Analyze conditions in a playbook")
    analyze_parser.add_argument("playbook", help="Path to playbook YAML file")
    analyze_parser.add_argument(
        "--output", "-o", 
        help="Path to output JSON file (optional)"
    )
    
    # Validate condition subcommand
    validate_parser = subparsers.add_parser("validate", help="Validate a single condition")
    validate_parser.add_argument("condition", help="Condition to validate")
    
    # Test condition subcommand
    test_parser = subparsers.add_parser("test", help="Test a condition with variables")
    test_parser.add_argument("condition", help="Condition to test")
    test_parser.add_argument(
        "--vars", "-v", 
        help="JSON string or path to JSON file with variables"
    )
    
    args = parser.parse_args()
    
    if args.command == "analyze":
        try:
            # Load playbook
            with open(args.playbook, 'r') as f:
                playbook_dict = yaml.safe_load(f)
            
            # Analyze conditions
            analysis = analyze_playbook_conditions(playbook_dict)
            
            # Print report
            print_condition_report(analysis)
            
            # Save to file if requested
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(analysis, f, indent=2)
                print(f"\nAnalysis saved to {args.output}")
                
        except Exception as e:
            logger.error(f"Error analyzing playbook: {str(e)}")
            sys.exit(1)
    
    elif args.command == "validate":
        try:
            valid, error = validate_condition(args.condition)
            if valid:
                print(f"Condition is valid: {args.condition}")
                variables = get_condition_variables(args.condition)
                if variables:
                    print(f"Referenced variables: {', '.join(variables)}")
                else:
                    print("No variables referenced in condition")
            else:
                print(f"Condition is invalid: {error}")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"Error validating condition: {str(e)}")
            sys.exit(1)
    
    elif args.command == "test":
        try:
            # Parse variables
            if args.vars:
                if args.vars.startswith('{'):
                    variables = json.loads(args.vars)
                else:
                    with open(args.vars, 'r') as f:
                        variables = json.load(f)
            else:
                variables = {}
            
            # Test the condition
            test_condition(args.condition, variables)
                
        except Exception as e:
            logger.error(f"Error testing condition: {str(e)}")
            sys.exit(1)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()