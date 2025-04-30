# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

from typing import Dict, List, Optional, Union, Any
import yaml
import json
from pydantic import BaseModel, Field
from fastapi import HTTPException, status
import logging
from datetime import datetime
from core.tools.github_mcp import GitHubMCPTool
from core.tools.secrets_manager import secrets

from .journey_agent import JourneyAgent
from ..tools.github_tool import GitHubTool

logger = logging.getLogger(__name__)

class DeploymentConfig(BaseModel):
    """Configuration for deployment process"""
    environment: str = Field(..., description="Target environment (e.g., staging, production)")
    branch: str = Field(..., description="Branch to deploy from")
    domain: str = Field(..., description="Target domain for deployment")
    build_command: str = Field(default="npm run build")
    auto_merge: bool = Field(default=False)
    require_approval: bool = Field(default=True)

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
        self.github_tool = GitHubMCPTool()
        self.active_deployments: Dict[str, Any] = {}
        
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

    async def setup_repository(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Set up a new repository with initial configuration"""
        try:
            # Create repository
            repo = await self.github_tool.create_repository(
                name=name,
                description=config.get("description", ""),
                private=config.get("private", False),
                auto_init=True
            )
            
            # Set up branch protection
            await self.setup_branch_protection(repo["name"], "main")
            
            # Initialize with basic files
            await self.initialize_repository(repo["name"], config)
            
            return repo
        except Exception as e:
            logger.error(f"Repository setup failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Repository setup failed: {str(e)}"
            )
            
    async def setup_branch_protection(self, repo_name: str, branch: str) -> None:
        """Configure branch protection rules"""
        try:
            protection_rules = {
                "required_status_checks": {
                    "strict": True,
                    "contexts": ["test", "lint", "build"]
                },
                "enforce_admins": True,
                "required_pull_request_reviews": {
                    "dismissal_restrictions": {},
                    "dismiss_stale_reviews": True,
                    "require_code_owner_reviews": True
                },
                "restrictions": None
            }
            
            await self.github_tool.update_branch_protection(
                repo=repo_name,
                branch=branch,
                rules=protection_rules
            )
        except Exception as e:
            logger.error(f"Branch protection setup failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Branch protection setup failed: {str(e)}"
            )
            
    async def initialize_repository(self, repo_name: str, config: Dict[str, Any]) -> None:
        """Initialize repository with necessary files and configurations"""
        try:
            files = [
                {
                    "path": ".github/workflows/ci.yml",
                    "content": self._generate_ci_workflow()
                },
                {
                    "path": ".github/workflows/deploy.yml",
                    "content": self._generate_deploy_workflow()
                },
                {
                    "path": "README.md",
                    "content": self._generate_readme(config)
                },
                {
                    "path": "docusaurus.config.js",
                    "content": self._generate_docusaurus_config(config)
                }
            ]
            
            await self.github_tool.push_files(
                repo=repo_name,
                files=files,
                message="Initial repository setup"
            )
        except Exception as e:
            logger.error(f"Repository initialization failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Repository initialization failed: {str(e)}"
            )
            
    def _generate_ci_workflow(self) -> str:
        """Generate GitHub Actions CI workflow"""
        return """
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm test
      
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run lint
      
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run build
"""

    def _generate_deploy_workflow(self) -> str:
        """Generate GitHub Actions deployment workflow"""
        return """
name: Deploy

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run build
      
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./build
"""

    def _generate_readme(self, config: Dict[str, Any]) -> str:
        """Generate README content"""
        return f"""
# {config.get('name', 'Documentation')}

{config.get('description', '')}

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm start
   ```

3. Build for production:
   ```bash
   npm run build
   ```

## Documentation

This site is built using [Docusaurus](https://docusaurus.io/), a modern static website generator.

## Contributing

Please read our [Contributing Guide](./CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
"""

    def _generate_docusaurus_config(self, config: Dict[str, Any]) -> str:
        """Generate Docusaurus configuration"""
        return f"""
const config = {{
  title: '{config.get("name", "Documentation")}',
  tagline: '{config.get("tagline", "")}',
  url: '{config.get("url", "https://your-domain.com")}',
  baseUrl: '/',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  favicon: 'img/favicon.ico',
  organizationName: '{config.get("org", "your-org")}',
  projectName: '{config.get("name", "docs")}',
  
  presets: [
    [
      '@docusaurus/preset-classic',
      {{
        docs: {{
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: 'https://github.com/{config.get("org", "your-org")}/{config.get("name", "docs")}/edit/main/',
        }},
        blog: {{
          showReadingTime: true,
          editUrl: 'https://github.com/{config.get("org", "your-org")}/{config.get("name", "docs")}/edit/main/blog/',
        }},
        theme: {{
          customCss: require.resolve('./src/css/custom.css'),
        }},
      }},
    ]],
  
  themeConfig: {{
    navbar: {{
      title: '{config.get("name", "Documentation")}',
      logo: {{
        alt: 'Logo',
        src: 'img/logo.svg',
      }},
      items: [
        {{
          type: 'doc',
          docId: 'intro',
          position: 'left',
          label: 'Documentation',
        }},
        {{to: '/blog', label: 'Blog', position: 'left'}},
        {{
          href: 'https://github.com/{config.get("org", "your-org")}/{config.get("name", "docs")}',
          label: 'GitHub',
          position: 'right',
        }},
      ],
    }},
    footer: {{
      style: 'dark',
      links: [
        {{
          title: 'Docs',
          items: [
            {{
              label: 'Getting Started',
              to: '/docs/intro',
            }},
          ],
        }},
        {{
          title: 'Community',
          items: [
            {{
              label: 'GitHub',
              href: 'https://github.com/{config.get("org", "your-org")}/{config.get("name", "docs")}',
            }},
          ],
        }},
      ],
      copyright: `Copyright © ${{new Date().getFullYear()}} {config.get("org", "Your Organization")}. Built with Docusaurus.`,
    }},
  }},
}};

module.exports = config;
"""

    async def create_deployment(self, config: DeploymentConfig) -> Dict[str, Any]:
        """Create and manage a new deployment"""
        try:
            deployment_id = f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create deployment branch
            await self.github_tool.create_branch(
                branch=f"deploy/{deployment_id}",
                from_branch=config.branch
            )
            
            # Update deployment configuration
            await self.update_deployment_config(deployment_id, config)
            
            # Create deployment pull request
            pr = await self.github_tool.create_pull_request(
                title=f"Deploy to {config.environment}",
                body=self._generate_deployment_pr_body(config),
                head=f"deploy/{deployment_id}",
                base=config.branch
            )
            
            self.active_deployments[deployment_id] = {
                "config": config.dict(),
                "status": "pending",
                "pr": pr,
                "created_at": datetime.now().isoformat()
            }
            
            return {
                "deployment_id": deployment_id,
                "pr_number": pr["number"],
                "status": "pending"
            }
        except Exception as e:
            logger.error(f"Deployment creation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Deployment creation failed: {str(e)}"
            )
            
    def _generate_deployment_pr_body(self, config: DeploymentConfig) -> str:
        """Generate deployment pull request description"""
        return f"""
## Deployment to {config.environment}

This PR deploys the latest changes to {config.environment}.

### Configuration
- Target Domain: {config.domain}
- Build Command: {config.build_command}
- Auto Merge: {'Yes' if config.auto_merge else 'No'}
- Requires Approval: {'Yes' if config.require_approval else 'No'}

### Pre-deployment Checklist
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Performance impact assessed
- [ ] Security review completed

### Post-deployment Verification
- [ ] Site accessible at {config.domain}
- [ ] Core functionality working
- [ ] No error spikes in monitoring

Please review and approve to proceed with deployment.
"""

    async def update_deployment_config(self, deployment_id: str, config: DeploymentConfig) -> None:
        """Update deployment configuration files"""
        try:
            files = [
                {
                    "path": f"config/deploy/{config.environment}.json",
                    "content": config.json(indent=2)
                }
            ]
            
            await self.github_tool.push_files(
                files=files,
                message=f"Update deployment configuration for {config.environment}"
            )
        except Exception as e:
            logger.error(f"Deployment config update failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Deployment config update failed: {str(e)}"
            )
            
    async def monitor_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Monitor deployment status and progress"""
        try:
            if deployment_id not in self.active_deployments:
                raise ValueError(f"Deployment {deployment_id} not found")
                
            deployment = self.active_deployments[deployment_id]
            pr_number = deployment["pr"]["number"]
            
            # Check PR status
            pr_status = await self.github_tool.get_pull_request_status(pr_number)
            
            # Check deployment status
            deployment_status = await self.github_tool.get_deployment_status(
                pr_number,
                deployment["config"]["environment"]
            )
            
            return {
                "deployment_id": deployment_id,
                "pr_status": pr_status,
                "deployment_status": deployment_status,
                "config": deployment["config"],
                "created_at": deployment["created_at"]
            }
        except Exception as e:
            logger.error(f"Deployment monitoring failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Deployment monitoring failed: {str(e)}"
            )
