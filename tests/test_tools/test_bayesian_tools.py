"""Tests for the Bayesian Tools."""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
import pymc as pm
import arviz as az

from core.tools.bayesian_tools import (
    PriorSpec,
    LikelihoodSpec,
    InferenceSpec,
    BayesianResult,
    update_beliefs,
    compute_bayes_factor,
    predict,
    _create_distribution,
    _extract_posterior_stats
)

@pytest.fixture
def mock_trace():
    """Create a mock InferenceData object."""
    mock = MagicMock(spec=az.InferenceData)
    mock.posterior = {
        'theta': MagicMock(
            mean=lambda: np.array([0.5]),
            std=lambda: np.array([0.1])
        )
    }
    return mock

@pytest.fixture
def sample_prior():
    """Create a sample prior specification."""
    return PriorSpec(
        distribution='normal',
        parameters={'mu': 0.0, 'sigma': 1.0}
    )

@pytest.fixture
def sample_likelihood():
    """Create a sample likelihood specification."""
    return LikelihoodSpec(
        distribution='normal',
        parameters={'mu': 0.0, 'sigma': 1.0},
        data=[1.0, 2.0, 3.0]
    )

@pytest.fixture
def sample_inference():
    """Create a sample inference specification."""
    return InferenceSpec(
        draws=100,
        tune=100,
        chains=2
    )

@pytest.mark.asyncio
async def test_update_beliefs_success(sample_prior, sample_likelihood, sample_inference, mock_trace):
    """Test successful belief updating."""
    with patch('pymc.Model'), \
         patch('pymc.sample', return_value=mock_trace), \
         patch('arviz.waic', return_value=MagicMock(waic=1.0)), \
         patch('arviz.loo', return_value=MagicMock(loo=2.0)), \
         patch('core.tools.bayesian_tools._extract_posterior_stats') as mock_extract:
        
        mock_extract.return_value = BayesianResult(
            posterior_mean=0.5,
            posterior_std=0.1,
            hdi_low=0.3,
            hdi_high=0.7,
            effective_sample_size=100.0,
            r_hat=1.01
        )
        
        result = await update_beliefs(sample_prior, sample_likelihood, sample_inference)
        
        assert result["success"]
        assert "results" in result
        assert result["results"]["posterior_mean"] == 0.5
        assert "diagnostics" in result
        assert result["diagnostics"]["waic"] == 1.0
        assert result["diagnostics"]["loo"] == 2.0

@pytest.mark.asyncio
async def test_update_beliefs_error(sample_prior, sample_likelihood):
    """Test error handling in belief updating."""
    with patch('pymc.Model', side_effect=Exception("Test error")):
        result = await update_beliefs(sample_prior, sample_likelihood)
        
        assert not result["success"]
        assert "error" in result
        assert "Test error" in result["error"]

def test_create_distribution_valid():
    """Test creating valid distributions."""
    spec = PriorSpec(
        distribution='normal',
        parameters={'mu': 0.0, 'sigma': 1.0}
    )
    
    dist = _create_distribution(spec)
    assert dist == pm.Normal

def test_create_distribution_invalid():
    """Test creating invalid distribution."""
    spec = PriorSpec(
        distribution='invalid',
        parameters={}
    )
    
    with pytest.raises(ValueError):
        _create_distribution(spec)

def test_extract_posterior_stats(mock_trace):
    """Test extracting posterior statistics."""
    with patch('arviz.hdi', return_value={'theta': np.array([0.3, 0.7])}), \
         patch('arviz.ess', return_value={'theta': np.array([100.0])}), \
         patch('arviz.rhat', return_value={'theta': np.array([1.01])}):
        
        result = _extract_posterior_stats(mock_trace, 'theta')
        
        assert isinstance(result, BayesianResult)
        assert result.posterior_mean == 0.5
        assert result.posterior_std == 0.1
        assert result.hdi_low == 0.3
        assert result.hdi_high == 0.7
        assert result.effective_sample_size == 100.0
        assert result.r_hat == 1.01

@pytest.mark.asyncio
async def test_compute_bayes_factor_success():
    """Test successful Bayes factor computation."""
    model1 = {
        "prior": {
            "distribution": "normal",
            "parameters": {"mu": 0.0, "sigma": 1.0}
        },
        "likelihood": {
            "distribution": "normal",
            "parameters": {"mu": 0.0, "sigma": 1.0}
        }
    }
    
    model2 = {
        "prior": {
            "distribution": "normal",
            "parameters": {"mu": 1.0, "sigma": 1.0}
        },
        "likelihood": {
            "distribution": "normal",
            "parameters": {"mu": 1.0, "sigma": 1.0}
        }
    }
    
    data = [1.0, 2.0, 3.0]
    
    with patch('pymc.Model'), \
         patch('pymc.sample', return_value=mock_trace), \
         patch('pymc.compute_log_marginal_likelihood', return_value=np.array([1.0])):
        
        result = await compute_bayes_factor(model1, model2, data)
        
        assert result["success"]
        assert "bayes_factor" in result
        assert "log_bayes_factor" in result

@pytest.mark.asyncio
async def test_compute_bayes_factor_error():
    """Test error handling in Bayes factor computation."""
    with patch('pymc.Model', side_effect=Exception("Test error")):
        result = await compute_bayes_factor({}, {}, [])
        
        assert not result["success"]
        assert "error" in result
        assert "Test error" in result["error"]

@pytest.mark.asyncio
async def test_predict_success():
    """Test successful prediction."""
    model = {
        "posterior": {
            "distribution": "normal",
            "parameters": {"mu": 0.0, "sigma": 1.0}
        },
        "likelihood": {
            "distribution": "normal",
            "parameters": {"mu": 0.0, "sigma": 1.0}
        }
    }
    
    posterior = {"mu": 0.0, "sigma": 1.0}
    x_new = [1.0, 2.0, 3.0]
    
    mock_posterior_predictive = MagicMock()
    mock_posterior_predictive.posterior_predictive = {
        'y_pred': MagicMock(
            mean=lambda dim: np.array([0.5, 0.6, 0.7]),
            std=lambda dim: np.array([0.1, 0.1, 0.1])
        )
    }
    
    with patch('pymc.Model'), \
         patch('pymc.sample_posterior_predictive', return_value=mock_posterior_predictive), \
         patch('arviz.hdi', return_value=MagicMock(y_pred=MagicMock(values=np.array([[0.3, 0.7]])))):
        
        result = await predict(model, posterior, x_new)
        
        assert result["success"]
        assert "predictions" in result
        assert "std" in result
        assert "intervals" in result
        assert len(result["predictions"]) == len(x_new)

@pytest.mark.asyncio
async def test_predict_error():
    """Test error handling in prediction."""
    with patch('pymc.Model', side_effect=Exception("Test error")):
        result = await predict({}, {}, [])
        
        assert not result["success"]
        assert "error" in result
        assert "Test error" in result["error"] 