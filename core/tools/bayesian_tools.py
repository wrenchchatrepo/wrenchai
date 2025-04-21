# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import logging
from typing import Dict, Any, Optional, List, Union
import numpy as np

# Singleton reference to the BayesianEngine
# This will be set by the system at startup
_bayesian_engine = None

def set_bayesian_engine(engine):
    """Set the Bayesian engine instance"""
    global _bayesian_engine
    _bayesian_engine = engine
    logging.info("Bayesian engine set for bayesian_tools")

def get_bayesian_engine():
    """Get the Bayesian engine instance"""
    global _bayesian_engine
    if _bayesian_engine is None:
        raise RuntimeError("Bayesian engine not initialized")
    return _bayesian_engine

async def update_beliefs(model: str, evidence: Dict[str, Any], 
                      sample_kwargs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Update beliefs in a Bayesian model
    
    Args:
        model: Name of the model to update
        evidence: Observed data {variable_name: value}
        sample_kwargs: Optional kwargs for pm.sample()
        
    Returns:
        Dictionary with posterior summaries for all variables
    """
    engine = get_bayesian_engine()
    
    try:
        result = engine.update_beliefs(model, evidence, sample_kwargs)
        return {
            "status": "success",
            "model": model,
            "evidence": evidence,
            "beliefs": result
        }
    except Exception as e:
        logging.error(f"Error updating beliefs: {e}")
        return {
            "status": "error",
            "model": model,
            "error": str(e)
        }

async def create_bayesian_model(model_name: str, variables: Dict[str, Dict]) -> Dict[str, Any]:
    """Create a new Bayesian model
    
    Args:
        model_name: Unique identifier for the model
        variables: Dictionary defining model variables and their priors
            Format: {
                'var_name': {
                    'type': 'continuous'|'binary'|'categorical',
                    'prior_mean': float, # for continuous
                    'prior_std': float,  # for continuous
                    'prior_prob': float, # for binary
                    'categories': List,  # for categorical
                    'prior_probs': List  # for categorical
                }
            }
    
    Returns:
        Status and model information
    """
    engine = get_bayesian_engine()
    
    try:
        engine.create_model(model_name, variables)
        return {
            "status": "success",
            "model": model_name,
            "variables": list(variables.keys())
        }
    except Exception as e:
        logging.error(f"Error creating Bayesian model: {e}")
        return {
            "status": "error",
            "model": model_name,
            "error": str(e)
        }

async def make_bayesian_decision(model: str, options: List[Dict], 
                            utility_function_str: str) -> Dict[str, Any]:
    """Make a decision using Bayesian decision theory
    
    Args:
        model: Name of the model to use
        options: List of option dictionaries
        utility_function_str: String representation of utility function
            Example: "lambda option, values: option['value'] * values['probability']"
    
    Returns:
        Best option and its expected utility
    """
    engine = get_bayesian_engine()
    
    try:
        # Compile the utility function
        # WARNING: This is unsafe in production - use a safer approach
        utility_function = eval(utility_function_str)
        
        best_option, expected_utility = engine.make_decision(
            model, options, utility_function
        )
        
        return {
            "status": "success",
            "model": model,
            "decision": best_option,
            "expected_utility": expected_utility,
            "all_options": len(options)
        }
    except Exception as e:
        logging.error(f"Error making Bayesian decision: {e}")
        return {
            "status": "error",
            "model": model,
            "error": str(e)
        }

async def get_belief_distribution(model: str, variable: str) -> Dict[str, Any]:
    """Get the distribution of a belief variable
    
    Args:
        model: Name of the model
        variable: Name of the variable
        
    Returns:
        Dictionary with distribution information
    """
    engine = get_bayesian_engine()
    
    try:
        summary = engine.get_belief_summary(model)
        
        if variable not in summary:
            raise ValueError(f"Variable {variable} not found in model {model}")
            
        return {
            "status": "success",
            "model": model,
            "variable": variable,
            "distribution": summary[variable]
        }
    except Exception as e:
        logging.error(f"Error getting belief distribution: {e}")
        return {
            "status": "error",
            "model": model,
            "variable": variable,
            "error": str(e)
        }