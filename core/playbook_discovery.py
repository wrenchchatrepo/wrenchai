#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import yaml
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("wrenchai.playbook_discovery")

class PlaybookManager:
    """Manager for discovering and loading playbooks"""
    
    def __init__(self, playbook_dirs: Optional[List[str]] = None):
        """Initialize the playbook manager
        
        Args:
            playbook_dirs: Optional list of directories to search for playbooks
        """
        self.playbook_dirs = playbook_dirs or [
            os.path.join(os.path.dirname(__file__), "..", "core", "playbooks"),
            os.path.expanduser("~/.wrenchai/playbooks")
        ]
        self.playbooks = {}
        self.load_all_playbooks()
    
    def load_all_playbooks(self) -> None:
        """Load all playbooks from configured directories"""
        self.playbooks = {}
        
        for directory in self.playbook_dirs:
            if not os.path.exists(directory):
                logger.debug(f"Playbook directory does not exist: {directory}")
                continue
                
            logger.debug(f"Searching for playbooks in {directory}")
            
            for filename in os.listdir(directory):
                if filename.endswith((".yaml", ".yml")):
                    path = os.path.join(directory, filename)
                    try:
                        playbook = self._load_playbook_file(path)
                        if playbook and "id" in playbook:
                            self.playbooks[playbook["id"]] = playbook
                            logger.debug(f"Loaded playbook: {playbook['id']}")
                    except Exception as e:
                        logger.warning(f"Error loading playbook {path}: {e}")
    
    def _load_playbook_file(self, path: str) -> Dict[str, Any]:
        """Load a playbook from a file
        
        Args:
            path: Path to the playbook file
            
        Returns:
            Playbook configuration dictionary
        """
        with open(path, 'r') as f:
            playbook = yaml.safe_load(f)
            
        # Add source path to the playbook
        playbook["source_path"] = path
        
        # Extract ID from the first step's metadata if it exists
        if isinstance(playbook, list) and len(playbook) > 0:
            for step in playbook:
                if isinstance(step, dict) and "step_id" in step and step["step_id"] == "metadata":
                    if "metadata" in step and "name" in step["metadata"]:
                        playbook = {
                            "id": step["metadata"]["name"],
                            "title": step["metadata"].get("description", "Unnamed Playbook"),
                            "description": step["metadata"].get("description", "No description"),
                            "steps": playbook,
                            "source_path": path
                        }
                        return playbook
        
        # If we couldn't extract metadata, generate ID from filename
        if "id" not in playbook:
            basename = os.path.basename(path)
            playbook_id = os.path.splitext(basename)[0]
            
            # If playbook is a list (steps), create a wrapper structure
            if isinstance(playbook, list):
                playbook = {
                    "id": playbook_id,
                    "title": playbook_id.replace('_', ' ').title(),
                    "description": "No description",
                    "steps": playbook,
                    "source_path": path
                }
            else:
                playbook["id"] = playbook_id
            
        return playbook
    
    def get_playbook(self, playbook_id: str) -> Optional[Dict[str, Any]]:
        """Get a playbook by ID
        
        Args:
            playbook_id: Playbook ID
            
        Returns:
            Playbook configuration dictionary or None if not found
        """
        return self.playbooks.get(playbook_id)
    
    def get_all_playbooks(self) -> List[Dict[str, Any]]:
        """Get all loaded playbooks
        
        Returns:
            List of playbook configuration dictionaries
        """
        return list(self.playbooks.values())
    
    def get_playbook_summary(self) -> List[Dict[str, str]]:
        """Get a summary of all playbooks
        
        Returns:
            List of dictionaries containing playbook ID, title, and description
        """
        return [
            {
                "id": playbook.get("id", ""),
                "title": playbook.get("title", playbook.get("name", "Unnamed")),
                "description": playbook.get("description", "No description")
            }
            for playbook in self.playbooks.values()
        ]
    
    def get_playbook_parameters(self, playbook_id: str) -> List[Dict[str, Any]]:
        """Get parameters for a playbook
        
        Args:
            playbook_id: Playbook ID
            
        Returns:
            List of parameter definitions
        """
        playbook = self.get_playbook(playbook_id)
        if not playbook:
            return []
            
        # Extract parameters from the playbook configuration
        params = playbook.get("parameters", [])
        
        # If parameters is a dictionary, convert to list format
        if isinstance(params, dict):
            params = [
                {"name": name, **definition}
                for name, definition in params.items()
            ]
            
        return params

# Singleton instance of the playbook manager
_manager_instance = None

def get_playbook_manager(playbook_dirs: Optional[List[str]] = None) -> PlaybookManager:
    """Get the singleton playbook manager instance
    
    Args:
        playbook_dirs: Optional list of directories to search for playbooks
        
    Returns:
        The PlaybookManager instance
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PlaybookManager(playbook_dirs)
    return _manager_instance