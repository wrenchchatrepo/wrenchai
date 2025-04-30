"""Tests for the Game Theory Tools."""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from core.tools.game_theory import (
    GameType,
    Strategy,
    Player,
    GameSpec,
    NashEquilibrium,
    find_nash_equilibria,
    analyze_strategies,
    evaluate_coalition,
    compute_shapley_values,
    _is_best_response,
    _find_2x2_mixed_equilibrium,
    _is_zero_sum
)

@pytest.fixture
def sample_strategy():
    """
    Creates a sample Strategy instance with predefined name, description, and probability.
    
    Returns:
        A Strategy object with name "strategy1", description "Test strategy", and probability 1.0.
    """
    return Strategy(
        name="strategy1",
        description="Test strategy",
        probability=1.0
    )

@pytest.fixture
def sample_player():
    """
    Creates a sample Player instance with two strategies and a 2x2 payoff matrix.
    
    Returns:
        Player: A player named "player1" with strategies "strategy1" and "strategy2", and a payoff matrix for a 2x2 game.
    """
    return Player(
        name="player1",
        strategies=[
            Strategy(name="strategy1"),
            Strategy(name="strategy2")
        ],
        payoff_matrix=[
            [3.0, 1.0],
            [0.0, 2.0]
        ]
    )

@pytest.fixture
def sample_game():
    """
    Creates a sample normal-form game with two players, each having two strategies and a 2x2 payoff matrix.
    
    Returns:
        GameSpec: A normal-form game specification for testing purposes.
    """
    return GameSpec(
        type=GameType.NORMAL_FORM,
        players=[
            Player(
                name="player1",
                strategies=[
                    Strategy(name="strategy1"),
                    Strategy(name="strategy2")
                ],
                payoff_matrix=[
                    [3.0, 1.0],
                    [0.0, 2.0]
                ]
            ),
            Player(
                name="player2",
                strategies=[
                    Strategy(name="strategy1"),
                    Strategy(name="strategy2")
                ],
                payoff_matrix=[
                    [2.0, 0.0],
                    [1.0, 3.0]
                ]
            )
        ]
    )

@pytest.fixture
def cooperative_game():
    """
    Creates a sample cooperative game specification with two players, each having one strategy and a single payoff value.
    
    Returns:
        GameSpec: A cooperative game with two players for use in tests.
    """
    return GameSpec(
        type=GameType.COOPERATIVE,
        cooperative=True,
        players=[
            Player(
                name="player1",
                strategies=[Strategy(name="cooperate")],
                payoff_matrix=[[5.0]]
            ),
            Player(
                name="player2",
                strategies=[Strategy(name="cooperate")],
                payoff_matrix=[[3.0]]
            )
        ]
    )

@pytest.mark.asyncio
async def test_find_nash_equilibria_success(sample_game):
    """Test successful Nash equilibria finding."""
    result = await find_nash_equilibria(sample_game)
    
    assert result["success"]
    assert "pure_equilibria" in result
    assert "mixed_equilibria" in result
    assert "analysis" in result
    assert result["analysis"]["game_type"] in ["zero_sum", "general_sum"]

@pytest.mark.asyncio
async def test_find_nash_equilibria_error():
    """Test error handling in Nash equilibria finding."""
    game = GameSpec(
        type=GameType.EXTENSIVE_FORM,
        players=[]
    )
    
    result = await find_nash_equilibria(game)
    
    assert not result["success"]
    assert "error" in result

def test_is_best_response():
    """Test best response checking."""
    payoff_matrices = [
        [[3.0, 1.0], [0.0, 2.0]],
        [[2.0, 1.0], [1.0, 3.0]]
    ]
    
    assert _is_best_response(0, 0, [0, 0], payoff_matrices)
    assert not _is_best_response(1, 0, [1, 0], payoff_matrices)

def test_find_2x2_mixed_equilibrium():
    """Test finding mixed equilibrium in 2x2 game."""
    payoff_matrices = [
        np.array([[3.0, 1.0], [0.0, 2.0]]),
        np.array([[2.0, 1.0], [1.0, 3.0]])
    ]
    
    result = _find_2x2_mixed_equilibrium(payoff_matrices)
    
    assert result is not None
    assert "probabilities" in result
    assert "expected_payoffs" in result

def test_is_zero_sum():
    """Test zero-sum game detection."""
    zero_sum_matrices = [
        np.array([[1.0, -1.0], [-1.0, 1.0]]),
        np.array([[-1.0, 1.0], [1.0, -1.0]])
    ]
    
    non_zero_sum_matrices = [
        np.array([[2.0, 1.0], [0.0, 3.0]]),
        np.array([[1.0, 2.0], [3.0, 0.0]])
    ]
    
    assert _is_zero_sum(zero_sum_matrices)
    assert not _is_zero_sum(non_zero_sum_matrices)

@pytest.mark.asyncio
async def test_analyze_strategies_success(sample_game):
    """Test successful strategy analysis."""
    result = await analyze_strategies(sample_game, "player1")
    
    assert result["success"]
    assert result["player"] == "player1"
    assert "metrics" in result
    assert "dominant_strategies" in result
    assert "strategy_analysis" in result
    assert len(result["strategy_analysis"]) == 2

@pytest.mark.asyncio
async def test_analyze_strategies_error(sample_game):
    """Test error handling in strategy analysis."""
    result = await analyze_strategies(sample_game, "nonexistent_player")
    
    assert not result["success"]
    assert "error" in result

@pytest.mark.asyncio
async def test_evaluate_coalition_success(cooperative_game):
    """Test successful coalition evaluation."""
    result = await evaluate_coalition(cooperative_game, ["player1", "player2"])
    
    assert result["success"]
    assert result["coalition"] == ["player1", "player2"]
    assert "analysis" in result
    assert "value" in result["analysis"]
    assert "relative_strength" in result["analysis"]

@pytest.mark.asyncio
async def test_evaluate_coalition_error(sample_game):
    """Test error handling in coalition evaluation."""
    result = await evaluate_coalition(sample_game, ["player1"])
    
    assert not result["success"]
    assert "error" in result

@pytest.mark.asyncio
async def test_compute_shapley_values_success(cooperative_game):
    """Test successful Shapley value computation."""
    result = await compute_shapley_values(cooperative_game)
    
    assert result["success"]
    assert "shapley_values" in result
    assert "analysis" in result
    assert len(result["shapley_values"]) == 2
    assert "total_value" in result["analysis"]
    assert "most_valuable_player" in result["analysis"]

@pytest.mark.asyncio
async def test_compute_shapley_values_error(sample_game):
    """Test error handling in Shapley value computation."""
    result = await compute_shapley_values(sample_game)
    
    assert not result["success"]
    assert "error" in result

def test_strategy_model():
    """Test Strategy model validation."""
    strategy = Strategy(name="test", probability=0.5)
    assert strategy.name == "test"
    assert strategy.probability == 0.5
    
    with pytest.raises(ValueError):
        Strategy(name="test", probability=1.5)

def test_player_model():
    """Test Player model validation."""
    player = Player(
        name="test",
        strategies=[Strategy(name="s1"), Strategy(name="s2")],
        payoff_matrix=[[1.0, 0.0], [0.0, 1.0]]
    )
    assert player.name == "test"
    assert len(player.strategies) == 2
    assert len(player.payoff_matrix) == 2

def test_game_spec_model():
    """Test GameSpec model validation."""
    game = GameSpec(
        type=GameType.NORMAL_FORM,
        players=[
            Player(
                name="p1",
                strategies=[Strategy(name="s1")],
                payoff_matrix=[[1.0]]
            )
        ]
    )
    assert game.type == GameType.NORMAL_FORM
    assert len(game.players) == 1
    assert not game.cooperative 