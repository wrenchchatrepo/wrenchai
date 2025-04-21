# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import pymc as pm
import numpy as np
import arviz as az
import logging
from typing import Dict, List, Any, Tuple, Optional, Callable

class BayesianEngine:
    """Core engine for probabilistic reasoning using PyMC"""
    
    def __init__(self):
        """Initialize the Bayesian engine"""
        self.belief_models = {}
        logging.info("Bayesian Engine initialized")
    
    def create_model(self, model_name: str, variables: Dict[str, Dict]) -> None:
        """Create a Bayesian model with specified variables
        
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
        """
        with pm.Model() as model:
            # Create model variables based on config
            model_vars = {}
            for var_name, var_config in variables.items():
                if var_config['type'] == 'continuous':
                    model_vars[var_name] = pm.Normal(
                        var_name,
                        mu=var_config.get('prior_mean', 0),
                        sigma=var_config.get('prior_std', 1)
                    )
                elif var_config['type'] == 'binary':
                    model_vars[var_name] = pm.Bernoulli(
                        var_name,
                        p=var_config.get('prior_prob', 0.5)
                    )
                elif var_config['type'] == 'categorical':
                    model_vars[var_name] = pm.Categorical(
                        var_name,
                        p=var_config.get('prior_probs', None),
                        categories=var_config.get('categories')
                    )
                # Add more distribution types as needed
            
            # Store the model for future use
            self.belief_models[model_name] = {
                'model': model,
                'vars': model_vars
            }
            
            logging.info(f"Created Bayesian model: {model_name} with variables: {list(variables.keys())}")
    
    def update_beliefs(self, model_name: str, 
                       evidence: Dict[str, Any],
                       sample_kwargs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Update beliefs given new evidence
        
        Args:
            model_name: Name of the model to update
            evidence: Observed data {variable_name: value}
            sample_kwargs: Optional kwargs for pm.sample()
            
        Returns:
            Dictionary with posterior summaries for all variables
        """
        if model_name not in self.belief_models:
            raise ValueError(f"Model {model_name} not found")
            
        model_data = self.belief_models[model_name]
        
        # Default sampling parameters
        sampling_params = {
            'draws': 1000,
            'tune': 500,
            'chains': 2,
            'return_inferencedata': True
        }
        
        # Update with user-provided parameters
        if sample_kwargs:
            sampling_params.update(sample_kwargs)
        
        with model_data['model']:
            # Add observed data based on evidence
            for var_name, value in evidence.items():
                if var_name in model_data['vars']:
                    # Create a potential to incorporate the evidence
                    pm.Potential(
                        f"obs_{var_name}", 
                        pm.Normal.dist(
                            mu=model_data['vars'][var_name], 
                            sigma=0.1
                        ).logp(value)
                    )
            
            # Sample posterior
            trace = pm.sample(**sampling_params)
            
            # Extract results
            posterior_summary = {}
            for var_name in model_data['vars'].keys():
                if var_name in trace.posterior:
                    var_samples = trace.posterior[var_name].values
                    posterior_summary[var_name] = {
                        'mean': float(var_samples.mean()),
                        'std': float(var_samples.std()),
                        'quantiles': {
                            '5%': float(np.percentile(var_samples, 5)),
                            '50%': float(np.percentile(var_samples, 50)),
                            '95%': float(np.percentile(var_samples, 95))
                        }
                    }
            
            # Store the updated trace
            self.belief_models[model_name]['last_trace'] = trace
            
            logging.info(f"Updated beliefs for model: {model_name} with evidence: {evidence}")
            return posterior_summary
            
    def make_decision(self, model_name: str, 
                     options: List[Dict], 
                     utility_function: Callable) -> Tuple[Dict, float]:
        """Make optimal decision based on current beliefs
        
        Args:
            model_name: Name of the model to use
            options: List of option dictionaries
            utility_function: Function that takes (option, model_values) and returns utility score
            
        Returns:
            Tuple of (best_option, expected_utility)
        """
        if model_name not in self.belief_models:
            raise ValueError(f"Model {model_name} not found")
            
        if 'last_trace' not in self.belief_models[model_name]:
            raise ValueError(f"Model {model_name} has no posterior samples yet. Run update_beliefs first.")
            
        # Get current belief state
        trace = self.belief_models[model_name]['last_trace']
        
        # Compute expected utility for each option
        option_utilities = []
        for option in options:
            # Calculate utility across all posterior samples
            utilities = []
            
            # Extract variable names and samples
            var_names = list(self.belief_models[model_name]['vars'].keys())
            samples = {var: trace.posterior[var].values.flatten() for var in var_names}
            
            # Number of samples
            n_samples = len(next(iter(samples.values())))
            
            # Calculate utility for each sample
            for i in range(n_samples):
                sample_values = {var: samples[var][i] for var in var_names}
                utility = utility_function(option, sample_values)
                utilities.append(utility)
            
            # Calculate expected utility
            expected_utility = float(np.mean(utilities))
            option_utilities.append((option, expected_utility))
        
        # Return option with highest expected utility
        if not option_utilities:
            raise ValueError("No options provided for decision making")
            
        best_option, best_utility = max(option_utilities, key=lambda x: x[1])
        logging.info(f"Decision made for model {model_name}: {best_option} with utility {best_utility:.4f}")
        
        return best_option, best_utility
    
    def get_belief_summary(self, model_name: str) -> Dict[str, Any]:
        """Get a summary of current beliefs for a model"""
        if model_name not in self.belief_models:
            raise ValueError(f"Model {model_name} not found")
            
        if 'last_trace' not in self.belief_models[model_name]:
            return {"status": "no_samples", "message": "No posterior samples available yet"}
            
        trace = self.belief_models[model_name]['last_trace']
        summary = az.summary(trace)
        
        # Convert to regular dictionary
        result = {}
        for var_name in self.belief_models[model_name]['vars'].keys():
            if var_name in summary.index:
                var_summary = summary.loc[var_name]
                result[var_name] = {
                    'mean': float(var_summary['mean']),
                    'std': float(var_summary['sd']),
                    'hdi_3%': float(var_summary['hdi_3%']),
                    'hdi_97%': float(var_summary['hdi_97%'])
                }
        
        return result