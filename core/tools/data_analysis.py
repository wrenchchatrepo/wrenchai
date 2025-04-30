# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

"""
Data Analysis Tool for statistical and analytical operations.

This module provides tools for:
- Descriptive statistics
- Correlation analysis
- Hypothesis testing
- Time series analysis
- Clustering analysis
- Feature importance
- Distribution analysis
- Outlier detection
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.cluster.vq import kmeans, vq
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any, List, Optional, Union, Tuple
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def analyze_data(
    data: Union[str, Dict, List], 
    analysis_type: str, 
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Analyze data using various statistical and analytical methods.
    
    Args:
        data: Input data (can be JSON string, dictionary, or list)
        analysis_type: Type of analysis to perform
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
            return _descriptive_analysis(df, params)
            
        elif analysis_type == 'correlation':
            return _correlation_analysis(df, params)
            
        elif analysis_type == 'hypothesis_test':
            return _hypothesis_test(df, params)
            
        elif analysis_type == 'time_series':
            return _time_series_analysis(df, params)
            
        elif analysis_type == 'clustering':
            return _clustering_analysis(df, params)
            
        elif analysis_type == 'feature_importance':
            return _feature_importance_analysis(df, params)
            
        elif analysis_type == 'distribution':
            return _distribution_analysis(df, params)
            
        elif analysis_type == 'outliers':
            return _outlier_analysis(df, params)
            
        else:
            return {'error': f'Unsupported analysis type: {analysis_type}'}
            
    except Exception as e:
        logger.error(f'Analysis failed: {str(e)}')
        return {'error': f'Analysis failed: {str(e)}'}

def _descriptive_analysis(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Perform descriptive statistical analysis.
    
    Args:
        df: Input DataFrame
        params: Analysis parameters
        
    Returns:
        Dict containing descriptive statistics
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    categorical_cols = df.select_dtypes(exclude=[np.number]).columns
    
    results = {
        'numeric': {
            'summary': df[numeric_cols].describe().to_dict(),
            'skewness': df[numeric_cols].skew().to_dict(),
            'kurtosis': df[numeric_cols].kurtosis().to_dict()
        },
        'categorical': {
            col: df[col].value_counts().to_dict() for col in categorical_cols
        },
        'missing_values': df.isnull().sum().to_dict(),
        'row_count': len(df),
        'column_count': len(df.columns)
    }
    
    if params.get('include_quartiles', False):
        results['numeric']['quartiles'] = {
            col: {
                'q1': np.percentile(df[col].dropna(), 25),
                'q3': np.percentile(df[col].dropna(), 75),
                'iqr': np.percentile(df[col].dropna(), 75) - np.percentile(df[col].dropna(), 25)
            } for col in numeric_cols
        }
    
    return results

def _correlation_analysis(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Perform correlation analysis.
    
    Args:
        df: Input DataFrame
        params: Analysis parameters
        
    Returns:
        Dict containing correlation analysis results
    """
    method = params.get('method', 'pearson')
    numeric_df = df.select_dtypes(include=[np.number])
    
    results = {
        'correlation_matrix': numeric_df.corr(method=method).to_dict(),
        'method': method
    }
    
    if params.get('include_pvalues', False):
        pvalues = {}
        for col1 in numeric_df.columns:
            pvalues[col1] = {}
            for col2 in numeric_df.columns:
                if col1 != col2:
                    _, pval = stats.pearsonr(numeric_df[col1].dropna(), numeric_df[col2].dropna())
                    pvalues[col1][col2] = pval
        results['pvalues'] = pvalues
    
    return results

def _hypothesis_test(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Perform hypothesis testing.
    
    Args:
        df: Input DataFrame
        params: Analysis parameters
        
    Returns:
        Dict containing hypothesis test results
    """
    test_type = params.get('test_type', 'ttest')
    group_col = params.get('group_column')
    value_col = params.get('value_column')
    
    if not (group_col and value_col):
        return {'error': 'group_column and value_column must be specified'}
        
    try:
        if test_type == 'ttest':
            groups = df[group_col].unique()
            if len(groups) != 2:
                return {'error': 'T-test requires exactly two groups'}
                
            group1 = df[df[group_col] == groups[0]][value_col]
            group2 = df[df[group_col] == groups[1]][value_col]
            
            statistic, pvalue = stats.ttest_ind(group1, group2)
            return {
                'test_type': 'ttest',
                'statistic': float(statistic),
                'pvalue': float(pvalue),
                'groups': groups.tolist()
            }
            
        elif test_type == 'anova':
            groups = [group[value_col].values for name, group in df.groupby(group_col)]
            statistic, pvalue = stats.f_oneway(*groups)
            return {
                'test_type': 'anova',
                'statistic': float(statistic),
                'pvalue': float(pvalue),
                'groups': df[group_col].unique().tolist()
            }
            
        else:
            return {'error': f'Unsupported test type: {test_type}'}
            
    except Exception as e:
        return {'error': f'Hypothesis test failed: {str(e)}'}

def _time_series_analysis(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Perform time series analysis.
    
    Args:
        df: Input DataFrame
        params: Analysis parameters
        
    Returns:
        Dict containing time series analysis results
    """
    time_col = params.get('time_column')
    value_col = params.get('value_column')
    
    if not (time_col and value_col):
        return {'error': 'time_column and value_column must be specified'}
        
    try:
        # Convert time column to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
            df[time_col] = pd.to_datetime(df[time_col])
            
        # Sort by time
        df = df.sort_values(time_col)
        
        # Calculate basic metrics
        results = {
            'total_periods': len(df),
            'start_date': df[time_col].min().isoformat(),
            'end_date': df[time_col].max().isoformat(),
            'mean': float(df[value_col].mean()),
            'std': float(df[value_col].std())
        }
        
        # Calculate rolling statistics if requested
        if params.get('include_rolling_stats', False):
            window = params.get('rolling_window', 7)
            rolling = df[value_col].rolling(window=window)
            results['rolling_stats'] = {
                'window': window,
                'rolling_mean': rolling.mean().dropna().tolist(),
                'rolling_std': rolling.std().dropna().tolist()
            }
        
        # Detect seasonality if requested
        if params.get('detect_seasonality', False):
            from statsmodels.tsa.seasonal import seasonal_decompose
            decomposition = seasonal_decompose(df[value_col], period=params.get('seasonality_period', 12))
            results['seasonality'] = {
                'trend': decomposition.trend.dropna().tolist(),
                'seasonal': decomposition.seasonal.dropna().tolist(),
                'residual': decomposition.resid.dropna().tolist()
            }
        
        return results
        
    except Exception as e:
        return {'error': f'Time series analysis failed: {str(e)}'}

def _clustering_analysis(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Perform clustering analysis.
    
    Args:
        df: Input DataFrame
        params: Analysis parameters
        
    Returns:
        Dict containing clustering analysis results
    """
    method = params.get('method', 'kmeans')
    n_clusters = params.get('n_clusters', 3)
    features = params.get('features', df.select_dtypes(include=[np.number]).columns.tolist())
    
    try:
        # Prepare data
        X = df[features].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        if method == 'kmeans':
            # Perform k-means clustering
            centroids, _ = kmeans(X_scaled, n_clusters)
            labels, _ = vq(X_scaled, centroids)
            
            # Calculate cluster statistics
            cluster_stats = {}
            for i in range(n_clusters):
                cluster_data = df[labels == i]
                cluster_stats[f'cluster_{i}'] = {
                    'size': len(cluster_data),
                    'mean': cluster_data[features].mean().to_dict(),
                    'std': cluster_data[features].std().to_dict()
                }
            
            return {
                'method': 'kmeans',
                'n_clusters': n_clusters,
                'labels': labels.tolist(),
                'cluster_stats': cluster_stats,
                'features_used': features
            }
            
        elif method == 'hierarchical':
            # Perform hierarchical clustering
            linkage_matrix = linkage(X_scaled, method=params.get('linkage_method', 'ward'))
            
            return {
                'method': 'hierarchical',
                'linkage_matrix': linkage_matrix.tolist(),
                'features_used': features
            }
            
        else:
            return {'error': f'Unsupported clustering method: {method}'}
            
    except Exception as e:
        return {'error': f'Clustering analysis failed: {str(e)}'}

def _feature_importance_analysis(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze feature importance using random forests.
    
    Args:
        df: Input DataFrame
        params: Analysis parameters
        
    Returns:
        Dict containing feature importance analysis results
    """
    target_col = params.get('target_column')
    if not target_col:
        return {'error': 'target_column must be specified'}
        
    try:
        # Prepare features and target
        features = df.select_dtypes(include=[np.number]).columns.tolist()
        features = [f for f in features if f != target_col]
        
        if not features:
            return {'error': 'No numeric features found'}
            
        X = df[features].values
        y = df[target_col].values
        
        # Choose model based on target type
        if df[target_col].dtype in ['int64', 'float64']:
            model = RandomForestRegressor(n_estimators=100, random_state=42)
        else:
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            
        # Fit model and get feature importance
        model.fit(X, y)
        importance = model.feature_importances_
        
        # Sort features by importance
        feature_importance = sorted(zip(features, importance), key=lambda x: x[1], reverse=True)
        
        return {
            'feature_importance': {
                feature: float(importance) for feature, importance in feature_importance
            },
            'model_type': model.__class__.__name__
        }
        
    except Exception as e:
        return {'error': f'Feature importance analysis failed: {str(e)}'}

def _distribution_analysis(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze data distributions.
    
    Args:
        df: Input DataFrame
        params: Analysis parameters
        
    Returns:
        Dict containing distribution analysis results
    """
    columns = params.get('columns', df.select_dtypes(include=[np.number]).columns.tolist())
    
    try:
        results = {}
        for col in columns:
            # Basic distribution statistics
            data = df[col].dropna()
            dist_stats = {
                'mean': float(data.mean()),
                'median': float(data.median()),
                'std': float(data.std()),
                'skewness': float(data.skew()),
                'kurtosis': float(data.kurtosis())
            }
            
            # Test for normality
            if len(data) >= 3:
                statistic, pvalue = stats.normaltest(data)
                dist_stats['normality_test'] = {
                    'statistic': float(statistic),
                    'pvalue': float(pvalue)
                }
            
            # Calculate percentiles
            percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
            dist_stats['percentiles'] = {
                f'p{p}': float(np.percentile(data, p)) for p in percentiles
            }
            
            results[col] = dist_stats
        
        return {'distributions': results}
        
    except Exception as e:
        return {'error': f'Distribution analysis failed: {str(e)}'}

def _outlier_analysis(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """Detect and analyze outliers.
    
    Args:
        df: Input DataFrame
        params: Analysis parameters
        
    Returns:
        Dict containing outlier analysis results
    """
    columns = params.get('columns', df.select_dtypes(include=[np.number]).columns.tolist())
    method = params.get('method', 'iqr')
    threshold = params.get('threshold', 1.5)
    
    try:
        results = {}
        for col in columns:
            data = df[col].dropna()
            
            if method == 'iqr':
                Q1 = data.quantile(0.25)
                Q3 = data.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                outliers = data[(data < lower_bound) | (data > upper_bound)]
                
                results[col] = {
                    'method': 'iqr',
                    'threshold': threshold,
                    'bounds': {
                        'lower': float(lower_bound),
                        'upper': float(upper_bound)
                    },
                    'outlier_count': len(outliers),
                    'outlier_percentage': float(len(outliers) / len(data) * 100),
                    'outlier_values': outliers.tolist()
                }
                
            elif method == 'zscore':
                z_scores = np.abs(stats.zscore(data))
                outliers = data[z_scores > threshold]
                
                results[col] = {
                    'method': 'zscore',
                    'threshold': threshold,
                    'outlier_count': len(outliers),
                    'outlier_percentage': float(len(outliers) / len(data) * 100),
                    'outlier_values': outliers.tolist()
                }
                
            else:
                return {'error': f'Unsupported outlier detection method: {method}'}
        
        return {'outliers': results}
        
    except Exception as e:
        return {'error': f'Outlier analysis failed: {str(e)}'} 