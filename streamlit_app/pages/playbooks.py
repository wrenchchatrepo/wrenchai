"""Playbooks page for WrenchAI application."""

import streamlit as st
from typing import Dict, List, Any, Optional

# Import utility functions
from wrenchai.streamlit_app.utils.session_state import StateKey, get_state, set_state
from wrenchai.streamlit_app.utils.logger import get_logger
from wrenchai.streamlit_app.utils.ui_components import status_indicator, display_error, display_success
from wrenchai.streamlit_app.components import (
    playbook_card, 
    execution_results_display, 
    playbook_form,
    section_container
)

# Setup logger
logger = get_logger(__name__)

st.set_page_config(
    page_title="WrenchAI - Playbooks",
    page_icon="🔧",
    layout="wide",
)

def main():
    """Main entry point for the playbooks page."""
    st.title("🧰 Playbooks")
    st.markdown("Browse and execute automation playbooks for your projects.")

    # Initialize necessary session state
    if StateKey.PLAYBOOK_FILTER.value not in st.session_state:
        set_state(StateKey.PLAYBOOK_FILTER, {"category": "all", "search": ""})
    
    # Get playbook list from session state or API
    playbook_list = get_state(StateKey.PLAYBOOK_LIST, [])
    
    # If no playbooks loaded yet, show loading message
    if not playbook_list:
        st.info("Loading playbooks... Please wait.")
    
    # Create layout with columns
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Search bar for playbooks
        search_query = st.text_input(
            "Search Playbooks",
            value=get_state([StateKey.PLAYBOOK_FILTER.value, "search"], ""),
            key="playbook_search"
        )
        
        # Update search filter in session state
        current_filter = get_state(StateKey.PLAYBOOK_FILTER, {"category": "all", "search": ""})
        current_filter["search"] = search_query
        set_state(StateKey.PLAYBOOK_FILTER, current_filter)
        
        # Filter playbooks based on category and search query
        filtered_playbooks = []
        category_filter = get_state([StateKey.PLAYBOOK_FILTER.value, "category"], "all")
        
        for playbook in playbook_list:
            # Apply category filter if not 'all'
            if category_filter != "all" and playbook.get("category") != category_filter:
                continue
                
            # Apply search filter if not empty
            if search_query and search_query.lower() not in playbook.get("name", "").lower() and \
               search_query.lower() not in playbook.get("description", "").lower():
                continue
                
            filtered_playbooks.append(playbook)
        
        # Display playbooks as cards in a grid
        if filtered_playbooks:
            with section_container("Available Playbooks"):
                # Display playbooks in a 2-column grid
                cols = st.columns(2)
                for i, playbook in enumerate(filtered_playbooks):
                    with cols[i % 2]:
                        playbook_card(
                            title=playbook.get("name", "Unnamed Playbook"),
                            description=playbook.get("description", "No description available"),
                            tags=[playbook.get("category", "general")],
                            button_text="Execute",
                            key=f"playbook_{playbook.get('id')}",
                            on_click=lambda pb=playbook: select_playbook(pb)  # Pass the playbook to callback
                        )
        else:
            st.warning("No playbooks match your search criteria.")
    
    with col2:
        # Sidebar-like panel for filters and options
        with section_container("Filters"):
            # Get configuration
            config = get_state(StateKey.CONFIG)
            
            # Playbook categories
            categories = ["all"] + list(config.playbooks.categories.keys()) \
                if hasattr(config, 'playbooks') and hasattr(config.playbooks, 'categories') \
                else ["all", "development", "analysis", "deployment"]
                
            category_names = ["All Categories"] + \
                [config.playbooks.categories.get(c, c.title()) for c in categories[1:]] \
                if hasattr(config, 'playbooks') and hasattr(config.playbooks, 'categories') \
                else ["All Categories", "Development", "Analysis", "Deployment"]
                
            # Create a dictionary for display names
            category_display = {categories[i]: category_names[i] for i in range(len(categories))}
            
            # Display category filter
            st.selectbox(
                "Category",
                categories,
                format_func=lambda x: category_display.get(x, x),
                index=categories.index(category_filter) if category_filter in categories else 0,
                key="category_filter",
                on_change=update_category_filter
            )
            
        # Recent playbooks section
        with section_container("Recent Playbooks"):
            execution_history = get_state(StateKey.EXECUTION_HISTORY, [])
            if execution_history:
                # Show last 5 unique playbooks from execution history
                unique_playbooks = []
                playbook_ids = set()
                
                for execution in reversed(execution_history):
                    playbook_id = execution.get("playbook_id")
                    if playbook_id and playbook_id not in playbook_ids and len(unique_playbooks) < 5:
                        # Find playbook details from playbook list
                        for playbook in playbook_list:
                            if playbook.get("id") == playbook_id:
                                unique_playbooks.append(playbook)
                                playbook_ids.add(playbook_id)
                                break
                
                # Show recent playbooks as links
                for playbook in unique_playbooks:
                    if st.button(
                        f"📋 {playbook.get('name', 'Unknown Playbook')}",
                        key=f"recent_{playbook.get('id')}"
                    ):
                        select_playbook(playbook)
            else:
                st.caption("No recent playbooks.")

def select_playbook(playbook: Dict[str, Any]):
    """Handle playbook selection.
    
    Args:
        playbook: The playbook dictionary to select
    """
    # Set selected playbook in session state
    set_state(StateKey.SELECTED_PLAYBOOK, playbook.get("id"))
    # Redirect to playbook executor page
    st.switch_page("wrenchai/streamlit_app/pages/playbook_executor.py")

def update_category_filter():
    """Update the category filter in session state."""
    current_filter = get_state(StateKey.PLAYBOOK_FILTER, {"category": "all", "search": ""})
    current_filter["category"] = st.session_state.category_filter
    set_state(StateKey.PLAYBOOK_FILTER, current_filter)

if __name__ == "__main__":
    main()