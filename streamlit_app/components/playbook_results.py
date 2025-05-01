"""Streamlit component for displaying playbook execution results."""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional

import streamlit as st
import pandas as pd
import plotly.express as px

class PlaybookResultDisplay:
    """Component for displaying playbook execution results."""
    
    def __init__(self):
        """Initialize the playbook result display component."""
        pass
    
    def render_summary(self, result: Dict[str, Any]):
        """Render a summary of the playbook execution.
        
        Args:
            result: Dictionary containing playbook execution results
        """
        if not result:
            st.warning("No result data available")
            return
            
        with st.container():
            # Header with key information
            st.subheader("Execution Summary")
            cols = st.columns(3)
            
            # Basic details
            with cols[0]:
                st.metric("Status", result.get("status", "Unknown"))
            with cols[1]:
                success_count = sum(1 for step in result.get("steps", []) 
                                  if step.get("status") == "completed")
                total_steps = len(result.get("steps", []))
                st.metric("Steps Completed", f"{success_count}/{total_steps}")
            with cols[2]:
                # Calculate total duration
                start_time = result.get("started_at")
                end_time = result.get("completed_at")
                duration = "N/A"
                if start_time and end_time:
                    try:
                        start_dt = datetime.fromisoformat(start_time)
                        end_dt = datetime.fromisoformat(end_time)
                        duration_secs = (end_dt - start_dt).total_seconds()
                        
                        # Format duration nicely
                        if duration_secs < 60:
                            duration = f"{duration_secs:.1f}s"
                        elif duration_secs < 3600:
                            duration = f"{duration_secs/60:.1f}m"
                        else:
                            duration = f"{duration_secs/3600:.1f}h"
                    except Exception:
                        pass
                st.metric("Duration", duration)
                
            # Overall result message
            if result.get("status") == "completed":
                st.success(result.get("message", "Playbook execution completed successfully"))
            elif result.get("status") == "failed":
                st.error(result.get("error", "Playbook execution failed"))
            else:
                st.info(result.get("message", "Execution in progress"))
    
    def render_step_details(self, steps: List[Dict[str, Any]]):
        """Render detailed information about each playbook step.
        
        Args:
            steps: List of step information dictionaries
        """
        if not steps:
            st.warning("No step data available")
            return
            
        st.subheader("Step Details")
        
        # Create DataFrame for table display
        df = pd.DataFrame([
            {
                "Step": i+1,
                "Name": step.get("name", f"Step {i+1}"),
                "Action": step.get("action", "Unknown"),
                "Status": step.get("status", "pending"),
                "Duration": self._calculate_step_duration(step),
                "Details": step
            }
            for i, step in enumerate(steps)
        ])
        
        # Style the table
        def color_status(val):
            colors = {
                "completed": "background-color: #c6ecc6",  # Light green
                "failed": "background-color: #ffc1c1",     # Light red
                "running": "background-color: #c1d6ff",    # Light blue
                "pending": "background-color: #f0f0f0"     # Light gray
            }
            return colors.get(val, "")
        
        # Apply styling
        st.dataframe(
            df.style.applymap(color_status, subset=["Status"]), 
            use_container_width=True,
            column_config={
                "Step": st.column_config.NumberColumn(width="small"),
                "Name": st.column_config.TextColumn(width="medium"),
                "Action": st.column_config.TextColumn(width="medium"),
                "Status": st.column_config.TextColumn(width="small"),
                "Duration": st.column_config.TextColumn(width="small"),
                "Details": st.column_config.Column(width=None),
            }
        )
        
        # Show details for each step in expanders
        for i, step in enumerate(steps):
            with st.expander(f"Step {i+1}: {step.get('name', '')}"):
                st.markdown(f"**Action:** {step.get('action', 'Unknown')}")
                st.markdown(f"**Status:** {step.get('status', 'Unknown')}")
                
                # Display step parameters
                if 'params' in step:
                    st.markdown("**Parameters:**")
                    st.json(step['params'])
                
                # Display step result
                if 'result' in step and step['result']:
                    st.markdown("**Result:**")
                    st.json(step['result'])
                
                # Display step error
                if 'error' in step and step['error']:
                    st.markdown("**Error:**")
                    st.error(step['error'])
    
    def render_visualization(self, steps: List[Dict[str, Any]]):
        """Render visualizations of playbook execution.
        
        Args:
            steps: List of step information dictionaries
        """
        if not steps:
            return
            
        st.subheader("Execution Visualization")
        
        # Count steps by status
        status_counts = {}
        for step in steps:
            status = step.get("status", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Create pie chart
        status_df = pd.DataFrame({
            "Status": status_counts.keys(),
            "Count": status_counts.values()
        })
        
        # Custom colors for different statuses
        color_map = {
            "completed": "#28a745",  # Green
            "failed": "#dc3545",    # Red
            "running": "#007bff",   # Blue
            "pending": "#6c757d",   # Gray
            "Unknown": "#ffc107"    # Yellow
        }
        
        fig = px.pie(
            status_df, 
            names="Status", 
            values="Count",
            title="Step Status Distribution",
            color="Status",
            color_discrete_map=color_map
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Create timeline of execution
        timeline_data = []
        for i, step in enumerate(steps):
            start_time = step.get("started_at")
            end_time = step.get("completed_at")
            if start_time:
                try:
                    # Convert to datetime objects if they exist
                    start_dt = datetime.fromisoformat(start_time)
                    end_dt = None
                    if end_time:
                        end_dt = datetime.fromisoformat(end_time)
                    else:
                        # If end time doesn't exist, use current time for in-progress steps
                        if step.get("status") == "running":
                            end_dt = datetime.now()
                    
                    # Only add if we have valid start/end times
                    if end_dt and end_dt > start_dt:
                        timeline_data.append({
                            "Step": f"{i+1}: {step.get('name', 'Step')}",
                            "Start": start_dt,
                            "End": end_dt,
                            "Duration": (end_dt - start_dt).total_seconds(),
                            "Status": step.get("status", "Unknown")
                        })
                except Exception:
                    # Skip invalid date formats
                    pass
        
        if timeline_data:
            timeline_df = pd.DataFrame(timeline_data)
            
            # Create a Gantt chart
            fig = px.timeline(
                timeline_df, 
                x_start="Start", 
                x_end="End", 
                y="Step",
                color="Status",
                color_discrete_map=color_map,
                title="Execution Timeline"
            )
            
            # Styling
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(height=max(300, len(timeline_data) * 40))
            
            st.plotly_chart(fig, use_container_width=True)
    
    def render_full_result(self, result: Dict[str, Any]):
        """Render the complete playbook result visualization.
        
        Args:
            result: Dictionary containing complete playbook execution result
        """
        if not result:
            st.warning("No result data available")
            return
            
        # Get steps from result
        steps = result.get("steps", [])
        
        # Render each section
        self.render_summary(result)
        st.markdown("---")
        self.render_step_details(steps)
        st.markdown("---")
        self.render_visualization(steps)
        
        # Raw data access
        with st.expander("View Raw Result Data"):
            st.json(result)
    
    def _calculate_step_duration(self, step: Dict[str, Any]) -> str:
        """Calculate the duration of a step.
        
        Args:
            step: Step information dictionary
            
        Returns:
            Formatted duration string
        """
        start_time = step.get("started_at")
        end_time = step.get("completed_at")
        
        if not start_time:
            return "N/A"
            
        try:
            start_dt = datetime.fromisoformat(start_time)
            
            if end_time:
                end_dt = datetime.fromisoformat(end_time)
            elif step.get("status") == "running":
                end_dt = datetime.now()
            else:
                return "N/A"
                
            duration_secs = (end_dt - start_dt).total_seconds()
            
            # Format duration nicely
            if duration_secs < 60:
                return f"{duration_secs:.1f}s"
            elif duration_secs < 3600:
                return f"{duration_secs/60:.1f}m"
            else:
                return f"{duration_secs/3600:.1f}h"
        except Exception:
            return "N/A"

def render_playbook_results(result: Optional[Dict[str, Any]] = None):
    """Render playbook execution results.
    
    Args:
        result: Dictionary containing playbook execution results. If None, displays a placeholder.
    """
    display = PlaybookResultDisplay()
    
    if result:
        display.render_full_result(result)
    else:
        st.info("No playbook execution results available.")
        st.markdown("Start a playbook execution to see results here.")