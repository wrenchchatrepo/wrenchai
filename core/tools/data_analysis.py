# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union
from scipy import stats
import json

def analyze_data(data: Union[str, Dict, List], analysis_type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Analyze data using various statistical and analytical methods.
    
    Args:
        data: Input data (can be JSON string, dictionary, or list)
        analysis_type: Type of analysis to perform (descriptive, correlation, hypothesis_test, etc.)
        params: Additional parameters for the analysis
        
    Returns:
        Dict containing analysis results
    """
    # Convert string input to Python object if needed
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return {'error': 'Invalid JSON string'}
            
    # Convert to DataFrame if needed
    if isinstance(data, (dict, list)):
        try:
            df = pd.DataFrame(data)
        except Exception as e:
            return {'error': f'Could not convert data to DataFrame: {str(e)}'}
    else:
        return {'error': 'Data must be JSON string, dictionary, or list'}
        
    # Initialize parameters
    params = params or {}
    
    try:
        if analysis_type == 'descriptive':
            return _descriptive_analysis(df)
            
        elif analysis_type == 'correlation':
            return _correlation_analysis(df, params.get('method', 'pearson'))
            
        elif analysis_type == 'hypothesis_test':
            return _hypothesis_test(df, params)
            
        elif analysis_type == 'time_series':
            return _time_series_analysis(df, params)
            
        elif analysis_type == 'clustering':
            return _clustering_analysis(df, params)
            
        else:
            return {'error': f'Unsupported analysis type: {analysis_type}'}
            
    except Exception as e:
        return {'error': f'Analysis failed: {str(e)}'}

def _descriptive_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Perform descriptive statistical analysis."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    results = {
        'summary': df.describe().to_dict(),
        'missing_values': df.isnull().sum().to_dict(),
        'data_types': df.dtypes.astype(str).to_dict()
    }
    
    if len(numeric_cols) > 0:
        results.update({
            'skewness': df[numeric_cols].skew().to_dict(),
            'kurtosis': df[numeric_cols].kurtosis().to_dict()
        })
        
    return results

def _correlation_analysis(df: pd.DataFrame, method: str = 'pearson') -> Dict[str, Any]:
    """Perform correlation analysis."""
    numeric_df = df.select_dtypes(include=[np.number])
    
    if method == 'pearson':
        corr_matrix = numeric_df.corr(method='pearson')
    elif method == 'spearman':
        corr_matrix = numeric_df.corr(method='spearman')
    else:
        return {'error': f'Unsupported correlation method: {method}'}
        
    return {
        'correlation_matrix': corr_matrix.to_dict(),
        'method': method
    }

def _hypothesis_test(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Perform statistical hypothesis testing."""
    test_type = params.get('test_type', 'ttest')
    col1 = params.get('column1')
    col2 = params.get('column2')
    
    if not col1 or col1 not in df.columns:
        return {'error': 'Invalid or missing column1'}
        
    if test_type == 'ttest':
        if not col2 or col2 not in df.columns:
            # One-sample t-test
            mu = params.get('mu', 0)
            stat, pval = stats.ttest_1samp(df[col1].dropna(), mu)
            return {
                'test': 'one_sample_ttest',
                'statistic': float(stat),
                'p_value': float(pval),
                'mu': mu
            }
        else:
            # Two-sample t-test
            stat, pval = stats.ttest_ind(df[col1].dropna(), df[col2].dropna())
            return {
                'test': 'two_sample_ttest',
                'statistic': float(stat),
                'p_value': float(pval)
            }
            
    elif test_type == 'normality':
        stat, pval = stats.normaltest(df[col1].dropna())
        return {
            'test': 'normality_test',
            'statistic': float(stat),
            'p_value': float(pval)
        }
        
    else:
        return {'error': f'Unsupported test type: {test_type}'}

def _time_series_analysis(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Perform time series analysis."""
    date_col = params.get('date_column')
    value_col = params.get('value_column')
    
    if not date_col or date_col not in df.columns:
        return {'error': 'Invalid or missing date_column'}
    if not value_col or value_col not in df.columns:
        return {'error': 'Invalid or missing value_column'}
        
    try:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)
        
        # Basic time series metrics
        results = {
            'total_observations': len(df),
            'date_range': {
                'start': df[date_col].min().isoformat(),
                'end': df[date_col].max().isoformat()
            },
            'basic_stats': df[value_col].describe().to_dict()
        }
        
        # Calculate rolling statistics if specified
        window = params.get('rolling_window')
        if window:
            rolling = df[value_col].rolling(window=window)
            results['rolling_statistics'] = {
                'mean': rolling.mean().dropna().tolist(),
                'std': rolling.std().dropna().tolist()
            }
            
        return results
        
    except Exception as e:
        return {'error': f'Time series analysis failed: {str(e)}'}

def _clustering_analysis(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Perform clustering analysis."""
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    
    # Get numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) == 0:
        return {'error': 'No numeric columns found for clustering'}
        
    # Prepare data
    X = df[numeric_cols]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Perform clustering
    n_clusters = params.get('n_clusters', 3)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(X_scaled)
    
    # Prepare results
    results = {
        'n_clusters': n_clusters,
        'cluster_sizes': pd.Series(clusters).value_counts().to_dict(),
        'cluster_centers': {
            f'cluster_{i}': center.tolist()
            for i, center in enumerate(kmeans.cluster_centers_)
        },
        'features_used': numeric_cols.tolist(),
        'inertia': float(kmeans.inertia_)
    }
    
    return results 