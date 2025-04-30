# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

"""
Bayesian update tools for belief updating and inference.

This module provides tools for Bayesian belief updating and inference using PyMC.
It supports various probability distributions and conjugate priors.
"""

import logging
from typing import Dict, Any, Optional, List, Union, Tuple
import numpy as np
import pymc as pm
import arviz as az
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

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

class PriorSpec(BaseModel):
    """Specification for a prior distribution."""
    distribution: str = Field(..., description="Distribution type (e.g., normal, beta)")
    parameters: Dict[str, float] = Field(..., description="Distribution parameters")

class LikelihoodSpec(BaseModel):
    """Specification for a likelihood function."""
    distribution: str = Field(..., description="Distribution type")
    parameters: Dict[str, float] = Field(..., description="Distribution parameters")
    data: List[float] = Field(..., description="Observed data")

class InferenceSpec(BaseModel):
    """Specification for inference settings."""
    draws: int = Field(default=1000, description="Number of posterior samples")
    tune: int = Field(default=1000, description="Number of tuning steps")
    chains: int = Field(default=4, description="Number of chains")
    target_accept: float = Field(default=0.8, description="Target acceptance rate")
    return_inferencedata: bool = Field(default=True, description="Return ArviZ InferenceData")

class BayesianResult(BaseModel):
    """Result of Bayesian inference."""
    posterior_mean: float = Field(..., description="Posterior mean")
    posterior_std: float = Field(..., description="Posterior standard deviation")
    hdi_low: float = Field(..., description="Lower bound of HDI")
    hdi_high: float = Field(..., description="Upper bound of HDI")
    effective_sample_size: float = Field(..., description="Effective sample size")
    r_hat: float = Field(..., description="R-hat convergence statistic")

def _create_distribution(spec: Union[PriorSpec, LikelihoodSpec]) -> Any:
    """Create a PyMC distribution from specification."""
    dist_map = {
        'normal': pm.Normal,
        'beta': pm.Beta,
        'gamma': pm.Gamma,
        'uniform': pm.Uniform,
        'exponential': pm.Exponential,
        'poisson': pm.Poisson,
        'bernoulli': pm.Bernoulli,
        'binomial': pm.Binomial,
    }
    
    if spec.distribution not in dist_map:
        raise ValueError(f"Unsupported distribution: {spec.distribution}")
        
    return dist_map[spec.distribution]

def _extract_posterior_stats(trace: az.InferenceData, var_name: str) -> BayesianResult:
    """Extract posterior statistics from trace."""
    posterior = trace.posterior[var_name]
    hdi = az.hdi(trace, var_names=[var_name])
    ess = az.ess(trace, var_names=[var_name])
    rhat = az.rhat(trace, var_names=[var_name])
    
    return BayesianResult(
        posterior_mean=float(posterior.mean()),
        posterior_std=float(posterior.std()),
        hdi_low=float(hdi[var_name][0]),
        hdi_high=float(hdi[var_name][1]),
        effective_sample_size=float(ess[var_name].mean()),
        r_hat=float(rhat[var_name].mean())
    )

async def update_beliefs(
    prior: PriorSpec,
    likelihood: LikelihoodSpec,
    inference: Optional[InferenceSpec] = None
) -> Dict[str, Any]:
    """Update beliefs using Bayesian inference.
    
    Args:
        prior: Prior distribution specification
        likelihood: Likelihood specification with data
        inference: Optional inference settings
        
    Returns:
        Dictionary containing inference results
    """
    try:
        inference = inference or InferenceSpec()
        
        # Create PyMC model
        with pm.Model() as model:
            # Set up prior
            prior_dist = _create_distribution(prior)
            theta = prior_dist('theta', **prior.parameters)
            
            # Set up likelihood
            likelihood_dist = _create_distribution(likelihood)
            y = likelihood_dist('y', **likelihood.parameters, observed=likelihood.data)
            
            # Run inference
            trace = pm.sample(
                draws=inference.draws,
                tune=inference.tune,
                chains=inference.chains,
                target_accept=inference.target_accept,
                return_inferencedata=inference.return_inferencedata
            )
        
        # Extract results
        results = _extract_posterior_stats(trace, 'theta')
        
        # Add model comparison metrics
        waic = az.waic(trace)
        loo = az.loo(trace)
        
        return {
            "success": True,
            "results": results.dict(),
            "diagnostics": {
                "waic": float(waic.waic),
                "loo": float(loo.loo),
                "warnings": [str(w) for w in trace.sample_stats.diverging.sum().values]
            }
        }
        
    except Exception as e:
        logger.error(f"Error in Bayesian update: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def compute_bayes_factor(
    model1: Dict[str, Any],
    model2: Dict[str, Any],
    data: List[float]
) -> Dict[str, Any]:
    """Compute Bayes factor for model comparison.
    
    Args:
        model1: First model specification
        model2: Second model specification
        data: Observed data
        
    Returns:
        Dictionary containing Bayes factor results
    """
    try:
        # Create and sample from both models
        with pm.Model() as model_1:
            prior1 = _create_distribution(PriorSpec(**model1["prior"]))
            theta1 = prior1('theta', **model1["prior"]["parameters"])
            likelihood1 = _create_distribution(LikelihoodSpec(**model1["likelihood"]))
            y1 = likelihood1('y', **model1["likelihood"]["parameters"], observed=data)
            trace1 = pm.sample(return_inferencedata=True)
            
        with pm.Model() as model_2:
            prior2 = _create_distribution(PriorSpec(**model2["prior"]))
            theta2 = prior2('theta', **model2["prior"]["parameters"])
            likelihood2 = _create_distribution(LikelihoodSpec(**model2["likelihood"]))
            y2 = likelihood2('y', **model2["likelihood"]["parameters"], observed=data)
            trace2 = pm.sample(return_inferencedata=True)
        
        # Compute Bayes factor using bridge sampling
        log_bf = pm.compute_log_marginal_likelihood(model_1, trace1) - \
                 pm.compute_log_marginal_likelihood(model_2, trace2)
        
        return {
            "success": True,
            "bayes_factor": float(np.exp(log_bf)),
            "log_bayes_factor": float(log_bf)
        }
        
    except Exception as e:
        logger.error(f"Error computing Bayes factor: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def predict(
    model: Dict[str, Any],
    posterior: Dict[str, Any],
    x_new: List[float]
) -> Dict[str, Any]:
    """Make predictions using posterior distribution.
    
    Args:
        model: Model specification
        posterior: Posterior distribution parameters
        x_new: New input values for prediction
        
    Returns:
        Dictionary containing predictions
    """
    try:
        with pm.Model() as pred_model:
            # Set up posterior predictive
            post_dist = _create_distribution(PriorSpec(**model["posterior"]))
            theta = post_dist('theta', **posterior)
            
            # Generate predictions
            pred_dist = _create_distribution(LikelihoodSpec(**model["likelihood"]))
            y_pred = pred_dist('y_pred', **model["likelihood"]["parameters"], shape=len(x_new))
            
            # Sample from posterior predictive
            posterior_predictive = pm.sample_posterior_predictive(
                samples=1000,
                var_names=['y_pred']
            )
        
        predictions = posterior_predictive.posterior_predictive['y_pred'].mean(dim=['chain', 'draw'])
        pred_std = posterior_predictive.posterior_predictive['y_pred'].std(dim=['chain', 'draw'])
        
        return {
            "success": True,
            "predictions": predictions.values.tolist(),
            "std": pred_std.values.tolist(),
            "intervals": az.hdi(posterior_predictive).y_pred.values.tolist()
        }
        
    except Exception as e:
        logger.error(f"Error in prediction: {str(e)}")
        return {
            "success": False,
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