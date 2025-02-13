# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import subprocess
from typing import Dict, List, Optional, Union

class GitHubTool:
    """Tool for interacting with GitHub via GitHub CLI."""
    
    def __init__(self, config: Dict[str, str]):
        """Initialize GitHub tool with configuration.
        
        Args:
            config: Dictionary containing:
                - token: GitHub PAT
                - repository: Repository name (owner/repo)
        """
        self.token = config.get('token') or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GitHub token is required")
            
        self.repository = config['repository']
        self._setup_environment()
        
    def _setup_environment(self) -> None:
        """Set up GitHub CLI environment."""
        os.environ['GITHUB_TOKEN'] = self.token
        
    def _run_command(self, command: str) -> str:
        """Run a GitHub CLI command.
        
        Args:
            command: GitHub CLI command to execute
            
        Returns:
            Command output as string
            
        Raises:
            RuntimeError: If command fails
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"GitHub CLI command failed: {e.stderr}")
            
    def create_issue(self, 
                    title: str,
                    body: str,
                    labels: Optional[List[str]] = None,
                    assignee: Optional[str] = None,
                    project: Optional[str] = None) -> str:
        """Create a GitHub issue.
        
        Args:
            title: Issue title
            body: Issue description/body
            labels: List of labels to apply
            assignee: GitHub username to assign
            project: Project board to add issue to
            
        Returns:
            Issue number as string
        """
        command = f'gh issue create --title "{title}" --body "{body}" --repo {self.repository}'
        
        if labels:
            command += f' --label "{",".join(labels)}"'
        if assignee:
            command += f' --assignee {assignee}'
            
        result = self._run_command(command)
        issue_number = result.split('/')[-1]
        
        if project:
            self.add_to_project(issue_number, project)
            
        return issue_number
        
    def update_issue(self,
                    number: Union[int, str],
                    title: Optional[str] = None,
                    body: Optional[str] = None,
                    labels: Optional[List[str]] = None,
                    assignee: Optional[str] = None,
                    state: Optional[str] = None) -> None:
        """Update a GitHub issue.
        
        Args:
            number: Issue number
            title: New title (optional)
            body: New body (optional)
            labels: Labels to add (optional)
            assignee: New assignee (optional)
            state: New state (open/closed) (optional)
        """
        command = f'gh issue edit {number} --repo {self.repository}'
        
        if title:
            command += f' --title "{title}"'
        if body:
            command += f' --body "{body}"'
        if labels:
            command += f' --add-label "{",".join(labels)}"'
        if assignee:
            command += f' --assignee {assignee}'
        if state:
            command += f' --state {state}'
            
        self._run_command(command)
        
    def add_to_project(self, issue_number: Union[int, str], project: str) -> None:
        """Add an issue to a project board.
        
        Args:
            issue_number: Issue number
            project: Project name
        """
        command = f'gh issue edit {issue_number} --add-project "{project}" --repo {self.repository}'
        self._run_command(command)
        
    def create_label(self,
                    name: str,
                    color: str,
                    description: Optional[str] = None) -> None:
        """Create a GitHub label.
        
        Args:
            name: Label name
            color: Color code (without #)
            description: Label description (optional)
        """
        command = f'gh label create "{name}" -c {color} --repo {self.repository}'
        
        if description:
            command += f' -d "{description}"'
            
        self._run_command(command)
        
    def create_project(self,
                      name: str,
                      columns: Optional[List[str]] = None) -> str:
        """Create a GitHub project board.
        
        Args:
            name: Project name
            columns: List of column names (optional)
            
        Returns:
            Project URL
        """
        command = f'gh project create "{name}" --repo {self.repository}'
        result = self._run_command(command)
        
        # TODO: Add columns once supported by gh CLI
        # Currently requires GraphQL API
        
        return result
        
    def setup_repository(self,
                        templates: bool = True,
                        branch_protection: bool = True,
                        labels: bool = True) -> None:
        """Set up repository with standard configuration.
        
        Args:
            templates: Whether to set up issue/PR templates
            branch_protection: Whether to set up branch protection
            labels: Whether to set up standard labels
        """
        if templates:
            # Create .github/ISSUE_TEMPLATE directory
            os.makedirs('.github/ISSUE_TEMPLATE', exist_ok=True)
            
            # TODO: Add template creation
            
        if branch_protection:
            # TODO: Add branch protection setup
            # Requires REST API
            pass
            
        if labels:
            # Create standard labels
            standard_labels = [
                ('bug', 'D93F0B', 'Something is not working'),
                ('enhancement', 'A2EEEF', 'New feature or request'),
                ('documentation', '0075CA', 'Documentation improvements'),
                ('help wanted', '008672', 'Extra attention is needed'),
                ('good first issue', '7057FF', 'Good for newcomers')
            ]
            
            for name, color, description in standard_labels:
                try:
                    self.create_label(name, color, description)
                except RuntimeError:
                    # Label might already exist
                    pass
