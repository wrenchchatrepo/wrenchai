"""
GitHub Tools for repository and content management.

This module provides functionality to:
- Create and manage repositories
- Handle file operations
- Manage issues and pull requests
- Search GitHub content
- Handle repository forks and branches
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class IssueState(str, Enum):
    """Issue states."""
    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"

class PullRequestState(str, Enum):
    """Pull request states."""
    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"

class SearchType(str, Enum):
    """GitHub search types."""
    REPOSITORIES = "repositories"
    CODE = "code"
    ISSUES = "issues"
    USERS = "users"

class IssueCreate(BaseModel):
    """Model for creating an issue."""
    title: str
    body: str
    assignees: Optional[List[str]] = None
    labels: Optional[List[str]] = None
    milestone: Optional[int] = None

class PullRequestCreate(BaseModel):
    """Model for creating a pull request."""
    title: str
    body: str
    head: str
    base: str = "main"
    draft: bool = False
    maintainer_can_modify: bool = True

class FileContent(BaseModel):
    """Model for file content operations."""
    path: str
    content: str
    message: str
    branch: Optional[str] = None
    sha: Optional[str] = None

class RepositoryCreate(BaseModel):
    """Model for repository creation."""
    name: str
    description: Optional[str] = None
    private: bool = False
    auto_init: bool = True

async def create_repository(
    repo_data: RepositoryCreate,
    owner: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new GitHub repository.
    
    Args:
        repo_data: Repository creation data
        owner: Repository owner (optional)
        
    Returns:
        Dict containing repository information
    """
    try:
        result = await mcp_github_create_repository(
            name=repo_data.name,
            description=repo_data.description,
            private=repo_data.private,
            autoInit=repo_data.auto_init
        )
        return {
            "success": True,
            "repository": result
        }
    except Exception as e:
        logger.error(f"Error creating repository: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def create_or_update_file(
    owner: str,
    repo: str,
    file_content: FileContent
) -> Dict[str, Any]:
    """Create or update a file in a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        file_content: File content and metadata
        
    Returns:
        Dict containing operation status
    """
    try:
        result = await mcp_github_create_or_update_file(
            owner=owner,
            repo=repo,
            path=file_content.path,
            content=file_content.content,
            message=file_content.message,
            branch=file_content.branch or "main",
            sha=file_content.sha
        )
        return {
            "success": True,
            "file": result
        }
    except Exception as e:
        logger.error(f"Error creating/updating file: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def get_file_contents(
    owner: str,
    repo: str,
    path: str,
    branch: Optional[str] = None
) -> Dict[str, Any]:
    """Get contents of a file or directory.
    
    Args:
        owner: Repository owner
        repo: Repository name
        path: Path to file or directory
        branch: Branch name (optional)
        
    Returns:
        Dict containing file contents
    """
    try:
        result = await mcp_github_get_file_contents(
            owner=owner,
            repo=repo,
            path=path,
            branch=branch
        )
        return {
            "success": True,
            "contents": result
        }
    except Exception as e:
        logger.error(f"Error getting file contents: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def create_issue(
    owner: str,
    repo: str,
    issue_data: IssueCreate
) -> Dict[str, Any]:
    """Create a new issue.
    
    Args:
        owner: Repository owner
        repo: Repository name
        issue_data: Issue creation data
        
    Returns:
        Dict containing issue information
    """
    try:
        result = await mcp_github_create_issue(
            owner=owner,
            repo=repo,
            title=issue_data.title,
            body=issue_data.body,
            assignees=issue_data.assignees,
            labels=issue_data.labels,
            milestone=issue_data.milestone
        )
        return {
            "success": True,
            "issue": result
        }
    except Exception as e:
        logger.error(f"Error creating issue: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def create_pull_request(
    owner: str,
    repo: str,
    pr_data: PullRequestCreate
) -> Dict[str, Any]:
    """Create a new pull request.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_data: Pull request creation data
        
    Returns:
        Dict containing pull request information
    """
    try:
        result = await mcp_github_create_pull_request(
            owner=owner,
            repo=repo,
            title=pr_data.title,
            body=pr_data.body,
            head=pr_data.head,
            base=pr_data.base,
            draft=pr_data.draft,
            maintainer_can_modify=pr_data.maintainer_can_modify
        )
        return {
            "success": True,
            "pull_request": result
        }
    except Exception as e:
        logger.error(f"Error creating pull request: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def search_repositories(
    query: str,
    page: Optional[int] = None,
    per_page: Optional[int] = None
) -> Dict[str, Any]:
    """Search GitHub repositories.
    
    Args:
        query: Search query
        page: Page number
        per_page: Results per page
        
    Returns:
        Dict containing search results
    """
    try:
        result = await mcp_github_search_repositories(
            query=query,
            page=page,
            perPage=per_page
        )
        return {
            "success": True,
            "repositories": result
        }
    except Exception as e:
        logger.error(f"Error searching repositories: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def search_code(
    query: str,
    page: Optional[int] = None,
    per_page: Optional[int] = None
) -> Dict[str, Any]:
    """Search code across GitHub.
    
    Args:
        query: Search query
        page: Page number
        per_page: Results per page
        
    Returns:
        Dict containing search results
    """
    try:
        result = await mcp_github_search_code(
            q=query,
            page=page,
            per_page=per_page
        )
        return {
            "success": True,
            "code": result
        }
    except Exception as e:
        logger.error(f"Error searching code: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def list_issues(
    owner: str,
    repo: str,
    state: Optional[IssueState] = None,
    labels: Optional[List[str]] = None,
    page: Optional[int] = None,
    per_page: Optional[int] = None
) -> Dict[str, Any]:
    """List repository issues.
    
    Args:
        owner: Repository owner
        repo: Repository name
        state: Issue state filter
        labels: Label filters
        page: Page number
        per_page: Results per page
        
    Returns:
        Dict containing issues list
    """
    try:
        result = await mcp_github_list_issues(
            owner=owner,
            repo=repo,
            state=state,
            labels=labels,
            page=page,
            per_page=per_page
        )
        return {
            "success": True,
            "issues": result
        }
    except Exception as e:
        logger.error(f"Error listing issues: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def list_pull_requests(
    owner: str,
    repo: str,
    state: Optional[PullRequestState] = None,
    head: Optional[str] = None,
    base: Optional[str] = None,
    page: Optional[int] = None,
    per_page: Optional[int] = None
) -> Dict[str, Any]:
    """List repository pull requests.
    
    Args:
        owner: Repository owner
        repo: Repository name
        state: PR state filter
        head: Head branch filter
        base: Base branch filter
        page: Page number
        per_page: Results per page
        
    Returns:
        Dict containing pull requests list
    """
    try:
        result = await mcp_github_list_pull_requests(
            owner=owner,
            repo=repo,
            state=state,
            head=head,
            base=base,
            page=page,
            per_page=per_page
        )
        return {
            "success": True,
            "pull_requests": result
        }
    except Exception as e:
        logger.error(f"Error listing pull requests: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def create_branch(
    owner: str,
    repo: str,
    branch: str,
    from_branch: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new branch.
    
    Args:
        owner: Repository owner
        repo: Repository name
        branch: New branch name
        from_branch: Source branch
        
    Returns:
        Dict containing branch information
    """
    try:
        result = await mcp_github_create_branch(
            owner=owner,
            repo=repo,
            branch=branch,
            from_branch=from_branch
        )
        return {
            "success": True,
            "branch": result
        }
    except Exception as e:
        logger.error(f"Error creating branch: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def fork_repository(
    owner: str,
    repo: str,
    organization: Optional[str] = None
) -> Dict[str, Any]:
    """Fork a repository.
    
    Args:
        owner: Repository owner
        repo: Repository name
        organization: Target organization
        
    Returns:
        Dict containing fork information
    """
    try:
        result = await mcp_github_fork_repository(
            owner=owner,
            repo=repo,
            organization=organization
        )
        return {
            "success": True,
            "fork": result
        }
    except Exception as e:
        logger.error(f"Error forking repository: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

async def merge_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
    commit_title: Optional[str] = None,
    commit_message: Optional[str] = None,
    merge_method: str = "merge"
) -> Dict[str, Any]:
    """Merge a pull request.
    
    Args:
        owner: Repository owner
        repo: Repository name
        pull_number: Pull request number
        commit_title: Title for merge commit
        commit_message: Message for merge commit
        merge_method: Merge method to use
        
    Returns:
        Dict containing merge status
    """
    try:
        result = await mcp_github_merge_pull_request(
            owner=owner,
            repo=repo,
            pull_number=pull_number,
            commit_title=commit_title,
            commit_message=commit_message,
            merge_method=merge_method
        )
        return {
            "success": True,
            "merge": result
        }
    except Exception as e:
        logger.error(f"Error merging pull request: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        } 