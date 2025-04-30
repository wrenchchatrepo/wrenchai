"""
Game Theory tools for strategic decision making.

This module provides tools for game theoretic analysis including:
- Nash equilibrium calculation
- Strategy analysis
- Payoff matrix evaluation
- Cooperative and non-cooperative game analysis
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum

logger = logging.getLogger(__name__)

class GameType(str, Enum):
    """Types of games supported."""
    NORMAL_FORM = "normal_form"
    EXTENSIVE_FORM = "extensive_form"
    COOPERATIVE = "cooperative"

class Strategy(BaseModel):
    """Representation of a player's strategy."""
    name: str = Field(..., description="Name of the strategy")
    description: Optional[str] = Field(None, description="Strategy description")
    probability: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Probability of playing this strategy"
    )

class Player(BaseModel):
    """Game player representation."""
    name: str = Field(..., description="Name of the player")
    strategies: List[Strategy] = Field(..., description="Available strategies")
    payoff_matrix: Optional[List[List[float]]] = Field(
        None,
        description="Payoff matrix for this player"
    )

class GameSpec(BaseModel):
    """Game specification."""
    type: GameType = Field(..., description="Type of game")
    players: List[Player] = Field(..., description="List of players")
    payoff_matrices: Optional[Dict[str, List[List[float]]]] = Field(
        None,
        description="Payoff matrices for all players"
    )
    cooperative: bool = Field(
        default=False,
        description="Whether the game is cooperative"
    )

class NashEquilibrium(BaseModel):
    """Representation of a Nash equilibrium."""
    strategies: Dict[str, str] = Field(
        ...,
        description="Mapping of player names to their equilibrium strategies"
    )
    payoffs: Dict[str, float] = Field(
        ...,
        description="Mapping of player names to their equilibrium payoffs"
    )
    is_pure: bool = Field(
        ...,
        description="Whether this is a pure strategy equilibrium"
    )

def _is_best_response(
    strategy_index: int,
    player_index: int,
    strategy_profile: List[int],
    payoff_matrices: List[List[List[float]]]
) -> bool:
    """
    Determines if a given strategy is a best response for a player in a specified strategy profile.
    
    Args:
        strategy_index: Index of the strategy being evaluated for the player.
        player_index: Index of the player whose strategy is being checked.
        strategy_profile: List of strategy indices representing the current strategy choices of all players.
        payoff_matrices: Payoff matrices for all players, where each matrix corresponds to a player.
    
    Returns:
        True if the specified strategy yields the highest payoff for the player given the other players' strategies; False otherwise.
    """
    current_payoff = payoff_matrices[player_index][strategy_profile[0]][strategy_profile[1]]
    
    for alt_strategy in range(len(payoff_matrices[player_index])):
        if alt_strategy == strategy_index:
            continue
        alt_profile = strategy_profile.copy()
        alt_profile[player_index] = alt_strategy
        alt_payoff = payoff_matrices[player_index][alt_profile[0]][alt_profile[1]]
        if alt_payoff > current_payoff:
            return False
    return True

async def find_nash_equilibria(game: GameSpec) -> Dict[str, Any]:
    """
    Calculates Nash equilibria for a normal form game.
    
    Finds all pure strategy Nash equilibria by evaluating best responses for each strategy profile. For 2x2 games, also attempts to compute a mixed strategy equilibrium. Returns a dictionary with lists of pure and mixed equilibria, analysis of equilibrium counts, and game type classification. If an error occurs, returns a failure status with an error message.
    
    Args:
        game: The game specification to analyze.
    
    Returns:
        A dictionary containing success status, lists of pure and mixed Nash equilibria, analysis details, or error information.
    """
    try:
        if game.type != GameType.NORMAL_FORM:
            raise ValueError("Nash equilibrium calculation only supported for normal form games")
            
        # Convert payoff matrices to numpy arrays
        payoff_matrices = []
        for player in game.players:
            if player.payoff_matrix is None:
                raise ValueError(f"Missing payoff matrix for player {player.name}")
            payoff_matrices.append(np.array(player.payoff_matrix))
            
        pure_equilibria = []
        mixed_equilibria = []
        
        # Find pure strategy Nash equilibria
        num_strategies = [len(player.strategies) for player in game.players]
        
        for i in range(num_strategies[0]):
            for j in range(num_strategies[1]):
                strategy_profile = [i, j]
                if all(_is_best_response(s, p, strategy_profile, payoff_matrices)
                      for p, s in enumerate(strategy_profile)):
                    pure_equilibria.append({
                        "strategies": {
                            game.players[0].name: game.players[0].strategies[i].name,
                            game.players[1].name: game.players[1].strategies[j].name
                        },
                        "payoffs": {
                            game.players[0].name: float(payoff_matrices[0][i][j]),
                            game.players[1].name: float(payoff_matrices[1][i][j])
                        }
                    })
        
        # For 2x2 games, attempt to find mixed strategy equilibrium
        if all(len(player.strategies) == 2 for player in game.players):
            try:
                mixed_eq = _find_2x2_mixed_equilibrium(payoff_matrices)
                if mixed_eq is not None:
                    mixed_equilibria.append(mixed_eq)
            except Exception as e:
                logger.warning(f"Failed to find mixed equilibrium: {str(e)}")
        
        return {
            "success": True,
            "pure_equilibria": pure_equilibria,
            "mixed_equilibria": mixed_equilibria,
            "analysis": {
                "num_pure_equilibria": len(pure_equilibria),
                "num_mixed_equilibria": len(mixed_equilibria),
                "game_type": "zero_sum" if _is_zero_sum(payoff_matrices) else "general_sum"
            }
        }
        
    except Exception as e:
        logger.error(f"Error finding Nash equilibria: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def _find_2x2_mixed_equilibrium(
    payoff_matrices: List[np.ndarray]
) -> Optional[Dict[str, Any]]:
    """
    Computes the mixed strategy Nash equilibrium for a 2x2 normal form game.
    
    Given two players' 2x2 payoff matrices, solves for the mixed strategy probabilities and expected payoffs. Returns None if no valid equilibrium exists or if an error occurs.
    
    Args:
        payoff_matrices: List containing two 2x2 numpy arrays representing the payoff matrices for each player.
    
    Returns:
        A dictionary with mixed strategy probabilities and expected payoffs for both players, or None if no valid equilibrium is found.
    """
    # Extract payoffs
    a11, a12, a21, a22 = payoff_matrices[0].flatten()
    b11, b12, b21, b22 = payoff_matrices[1].flatten()
    
    try:
        # Solve for probabilities
        p = (b22 - b21) / (b11 - b12 - b21 + b22)
        q = (a22 - a12) / (a11 - a21 - a12 + a22)
        
        # Check if valid probabilities
        if not (0 <= p <= 1 and 0 <= q <= 1):
            return None
            
        # Calculate expected payoffs
        exp_payoff1 = p * (q * a11 + (1-q) * a12) + (1-p) * (q * a21 + (1-q) * a22)
        exp_payoff2 = q * (p * b11 + (1-p) * b21) + (1-q) * (p * b12 + (1-p) * b22)
        
        return {
            "probabilities": {
                "player1": [float(p), float(1-p)],
                "player2": [float(q), float(1-q)]
            },
            "expected_payoffs": {
                "player1": float(exp_payoff1),
                "player2": float(exp_payoff2)
            }
        }
    except:
        return None

def _is_zero_sum(payoff_matrices: List[np.ndarray]) -> bool:
    """
    Determines whether a two-player game is zero-sum based on payoff matrices.
    
    Args:
        payoff_matrices: A list containing the payoff matrices for both players.
    
    Returns:
        True if the sum of the two payoff matrices is approximately zero for all entries, indicating a zero-sum game; otherwise, False.
    """
    return np.allclose(payoff_matrices[0] + payoff_matrices[1], 0)

async def analyze_strategies(
    game: GameSpec,
    player_name: str
) -> Dict[str, Any]:
    """
    Analyzes the strategies of a specified player in a game.
    
    Evaluates payoff statistics for each strategy, identifies dominant pure strategies, and summarizes overall payoff metrics for the player. Returns a dictionary with analysis results or error information if the player or payoff matrix is missing.
    
    Args:
        game: The game specification containing players and payoff matrices.
        player_name: The name of the player whose strategies are to be analyzed.
    
    Returns:
        A dictionary with success status, player name, overall payoff metrics, dominant pure strategies, and detailed per-strategy payoff statistics. If analysis fails, returns an error message.
    """
    try:
        # Find player
        player = next((p for p in game.players if p.name == player_name), None)
        if player is None:
            raise ValueError(f"Player {player_name} not found")
            
        if player.payoff_matrix is None:
            raise ValueError(f"Missing payoff matrix for player {player_name}")
            
        payoff_matrix = np.array(player.payoff_matrix)
        
        # Calculate various metrics
        min_payoff = float(np.min(payoff_matrix))
        max_payoff = float(np.max(payoff_matrix))
        avg_payoff = float(np.mean(payoff_matrix))
        
        # Find dominant strategies
        dominant_pure = []
        for i, strat in enumerate(player.strategies):
            if all(payoff_matrix[i][j] >= payoff_matrix[k][j]
                   for j in range(payoff_matrix.shape[1])
                   for k in range(payoff_matrix.shape[0])
                   if k != i):
                dominant_pure.append(strat.name)
        
        return {
            "success": True,
            "player": player_name,
            "metrics": {
                "min_payoff": min_payoff,
                "max_payoff": max_payoff,
                "avg_payoff": avg_payoff,
                "payoff_range": max_payoff - min_payoff
            },
            "dominant_strategies": {
                "pure": dominant_pure,
                "exists": len(dominant_pure) > 0
            },
            "strategy_analysis": [
                {
                    "strategy": strat.name,
                    "min_payoff": float(np.min(payoff_matrix[i])),
                    "max_payoff": float(np.max(payoff_matrix[i])),
                    "avg_payoff": float(np.mean(payoff_matrix[i]))
                }
                for i, strat in enumerate(player.strategies)
            ]
        }
        
    except Exception as e:
        logger.error(f"Error analyzing strategies: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def evaluate_coalition(
    game: GameSpec,
    coalition: List[str]
) -> Dict[str, Any]:
    """
    Evaluates the value and relative strength of a coalition in a cooperative game.
    
    Args:
        coalition: List of player names forming the coalition.
    
    Returns:
        A dictionary with success status and coalition analysis, including total value,
        relative strength compared to all players, coalition size, and proportion of players.
        If the game is not cooperative or coalition members are invalid, returns an error.
    """
    try:
        if not game.cooperative:
            raise ValueError("Coalition analysis only available for cooperative games")
            
        # Validate coalition members
        for player_name in coalition:
            if not any(p.name == player_name for p in game.players):
                raise ValueError(f"Player {player_name} not found in game")
        
        # Calculate coalition value (simplified)
        coalition_value = sum(
            sum(sum(row) for row in (p.payoff_matrix or []))
            for p in game.players
            if p.name in coalition
        )
        
        # Calculate relative strength
        total_value = sum(
            sum(sum(row) for row in (p.payoff_matrix or []))
            for p in game.players
        )
        
        return {
            "success": True,
            "coalition": coalition,
            "analysis": {
                "value": float(coalition_value),
                "relative_strength": float(coalition_value / total_value if total_value != 0 else 0),
                "size": len(coalition),
                "proportion_of_players": len(coalition) / len(game.players)
            }
        }
        
    except Exception as e:
        logger.error(f"Error evaluating coalition: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def compute_shapley_values(game: GameSpec) -> Dict[str, Any]:
    """
    Computes Shapley values for each player in a cooperative game.
    
    Calculates an approximate marginal contribution for each player based on the sum of other players' payoff matrices. Returns a dictionary with Shapley values, total value, and the most valuable player.
    """
    try:
        if not game.cooperative:
            raise ValueError("Shapley values only available for cooperative games")
            
        n = len(game.players)
        shapley_values = {}
        
        for i, player in enumerate(game.players):
            value = 0
            for j in range(n):
                if j != i:
                    # Calculate marginal contribution
                    coalition_with = sum(sum(row) for row in (game.players[j].payoff_matrix or []))
                    coalition_without = 0
                    value += (coalition_with - coalition_without) / n
                    
            shapley_values[player.name] = float(value)
        
        return {
            "success": True,
            "shapley_values": shapley_values,
            "analysis": {
                "total_value": sum(shapley_values.values()),
                "most_valuable_player": max(shapley_values.items(), key=lambda x: x[1])[0]
            }
        }
        
    except Exception as e:
        logger.error(f"Error computing Shapley values: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        } 