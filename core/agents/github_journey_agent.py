# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Optional, Union
import yaml
import json

from .journey_agent import JourneyAgent
from ..tools.github_tool import GitHubTool

class GitHubJourneyAgent(JourneyAgent):
    """Journey Agent specialized for GitHub project management."""
    
    def __init__(self, name: str, config_path: str):
        """Initialize GitHub Journey Agent.
        
        Args:
            name: Agent name
            config_path: Path to agent configuration YAML
        """
        super().__init__(name, config_path)
        self.github = self._setup_github_tool()
        
    def _setup_github_tool(self) -> GitHubTool:
        """Set up GitHub tool from configuration.
        
        Returns:
            Configured GitHubTool instance
        """
        return GitHubTool({
            'token': self.config.get('github_token'),
            'repository': self.config.get('github_repository')
        })
        
    def create_issues_from_template(self,
                                  template: str,
                                  tasks: List[Dict],
                                  project: Optional[str] = None) -> List[str]:
        """Create multiple issues from a template.
        
        Args:
            template: Template name to use
            tasks: List of task data dictionaries
            project: Project board to add issues to (optional)
            
        Returns:
            List of created issue numbers
        """
        issue_numbers = []
        
        for task in tasks:
            # Format issue body using template
            body = self._format_issue_body(template, task)
            
            # Create issue
            issue_number = self.github.create_issue(
                title=task['title'],
                body=body,
                labels=task.get('labels', []),
                assignee=task.get('assignee'),
                project=project
            )
            
            issue_numbers.append(issue_number)
            
            # Add dependencies if specified
            if 'dependencies' in task:
                self._add_dependencies(issue_number, task['dependencies'])
                
        return issue_numbers
        
    def _format_issue_body(self, template: str, task: Dict) -> str:
        """Format issue body using task data.
        
        Args:
            template: Template identifier (not used, kept for API compatibility)
            task: Task data dictionary
            
        Returns:
            Formatted issue body
        """
        # Create issue body directly from task data
        body = f"## Task: {task.get('title', '')}\n\n"
        
        # Add description if available
        if 'description' in task:
            body += f"## Description\n{task['description']}\n\n"
            
        # Add objectives if available
        if 'objectives' in task:
            body += "## Objectives\n"
            objectives = task['objectives']
            if isinstance(objectives, list):
                for objective in objectives:
                    body += f"- {objective}\n"
            else:
                body += f"{objectives}\n\n"
                
        # Add acceptance criteria if available
        if 'acceptance_criteria' in task:
            body += "## Acceptance Criteria\n"
            criteria = task['acceptance_criteria']
            if isinstance(criteria, list):
                for criterion in criteria:
                    body += f"- [ ] {criterion}\n"
            else:
                body += f"{criteria}\n\n"
        
        return body
        
    def _add_dependencies(self, issue_number: str, dependencies: List[str]) -> None:
        """Add dependency references to issue body.
        
        Args:
            issue_number: Issue number to update
            dependencies: List of dependent issue numbers
        """
        dependency_text = "\n\n## Dependencies\n"
        for dep in dependencies:
            dependency_text += f"- [ ] #{dep}\n"
            
        # Update issue body
        self.github.update_issue(
            number=issue_number,
            body=f"{self._get_issue_body(issue_number)}{dependency_text}"
        )
        
    def _get_issue_body(self, issue_number: str) -> str:
        """Get current issue body.
        
        Args:
            issue_number: Issue number
            
        Returns:
            Current issue body text
        """
        # Use gh api to get issue body
        result = self.github.run_gh_command(
            ['api', f'/repos/{self.config["github_repository"]}/issues/{issue_number}', '--jq', '.body']
        )
        return result.strip() if result else ""
        
    def setup_project_board(self,
                          name: str,
                          columns: List[str],
                          automation: Optional[Dict] = None) -> str:
        """Set up a new project board.
        
        Args:
            name: Project board name
            columns: List of column names
            automation: Automation rules (optional)
            
        Returns:
            Project URL
        """
        # Create project
        project_url = self.github.create_project(name, columns)
        
        # Add automation rules if specified
        if automation:
            project_id = project_url.split('/')[-1]
            
            # Configure automation rules using the API
            for rule in automation.get('rules', []):
                trigger = rule.get('trigger', {})
                action = rule.get('action', {})
                
                # Create automation rule
                self.github.run_gh_command([
                    'api',
                    f'/projects/{project_id}/automation/rules',
                    '-X', 'POST',
                    '-F', f'event_type={trigger.get("event")}',
                    '-F', f'action_type={action.get("type")}',
                    '-F', f'configuration={json.dumps(action.get("config", {}))}'
                ])
        
        return project_url
        
    def manage_labels(self,
                     labels: Optional[List[Dict]] = None,
                     updates: Optional[List[Dict]] = None) -> None:
        """Manage repository labels.
        
        Args:
            labels: List of new labels to create
            updates: List of label updates
        """
        if labels:
            for label in labels:
                self.github.create_label(
                    name=label['name'],
                    color=label['color'],
                    description=label.get('description')
                )
                
        # Update existing labels
        if updates:
            for update in updates:
                old_name = update.get('old_name')
                if not old_name:
                    continue
                    
                # Update label using the API
                self.github.run_gh_command([
                    'api',
                    f'/repos/{self.config["github_repository"]}/labels/{old_name}',
                    '-X', 'PATCH',
                    '-F', f'new_name={update.get("new_name", old_name)}',
                    '-F', f'color={update.get("color", "")}',
                    '-F', f'description={update.get("description", "")}'
                ])
