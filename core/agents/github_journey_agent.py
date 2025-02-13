# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Optional, Union
import yaml

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
        """Format issue body using template and task data.
        
        Args:
            template: Template name
            task: Task data dictionary
            
        Returns:
            Formatted issue body
        """
        # Load template
        template_path = f"core/playbooks/github_playbooks/templates/{template}.md"
        with open(template_path, 'r') as f:
            template_content = f.read()
            
        # Replace placeholders with task data
        body = template_content
        for key, value in task.items():
            if key not in ['title', 'labels', 'assignee', 'dependencies']:
                placeholder = f"{{{key}}}"
                body = body.replace(placeholder, str(value))
                
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
        # TODO: Implement using gh api
        return ""
        
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
        
        # TODO: Add automation rules once supported
        
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
                
        # TODO: Implement label updates once supported by gh CLI
