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
    """
    Creates a new GitHub repository with the specified settings.
    
    Args:
        repo_data: Repository creation parameters including name, description, privacy, and initialization options.
        owner: Optional repository owner.
    
    Returns:
        A dictionary indicating success and containing repository information on success, or an error message on failure.
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
    """
    Creates or updates a file in the specified GitHub repository.
    
    Attempts to create a new file or update an existing file at the given path using the provided content and metadata. Returns a dictionary indicating success and the resulting file information, or an error message on failure.
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
    """
    Retrieves the contents of a file or directory from a GitHub repository.
    
    Args:
        owner: The username or organization that owns the repository.
        repo: The name of the repository.
        path: The path to the file or directory within the repository.
        branch: The branch name to retrieve contents from (optional).
    
    Returns:
        A dictionary with "success": True and the contents if retrieval is successful,
        or "success": False and an error message if retrieval fails.
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
    """
    Creates a new issue in the specified repository.
    
    Attempts to create an issue using the provided data. Returns a dictionary indicating success and the created issue information, or an error message if the operation fails.
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
    """
    Creates a new pull request in the specified repository.
    
    Args:
        owner: The username or organization that owns the repository.
        repo: The name of the repository.
        pr_data: Data specifying the pull request's title, body, source branch, target branch, draft status, and maintainer modification permission.
    
    Returns:
        A dictionary with "success": True and pull request information if successful, or "success": False and an error message if creation fails.
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
    """
    Searches for GitHub repositories matching the specified query.
    
    Args:
        query: The search keywords and qualifiers.
        page: Optional page number for pagination.
        per_page: Optional number of results per page.
    
    Returns:
        A dictionary with "success": True and a list of repositories if the search is successful,
        or "success": False and an error message if the search fails.
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
    """
    Searches code across GitHub using the specified query and optional pagination.
    
    Args:
        query: The search query string.
        page: Optional page number for paginated results.
        per_page: Optional number of results per page.
    
    Returns:
        A dictionary with "success": True and the search results under "code" on success,
        or "success": False and an error message under "error" on failure.
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
    """
    Retrieves a list of issues from a GitHub repository with optional filtering.
    
    Args:
        state: Filter issues by their state (e.g., open, closed, all).
        labels: Filter issues by one or more labels.
        page: Page number for pagination.
        per_page: Number of results per page.
    
    Returns:
        A dictionary with a success flag and either the list of issues or an error message.
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
    """
    Retrieves a list of pull requests for a repository, with optional filtering by state, head branch, base branch, and pagination.
    
    Args:
        state: Filter pull requests by their state (e.g., open, closed, all).
        head: Filter by the name of the branch where changes are implemented.
        base: Filter by the name of the branch you want the changes pulled into.
        page: Page number for pagination.
        per_page: Number of results per page.
    
    Returns:
        A dictionary with "success" indicating the operation result, and either a "pull_requests" list on success or an "error" message on failure.
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
    """
    Creates a new branch in the specified repository, optionally from a given source branch.
    
    Args:
        branch: Name of the new branch to create.
        from_branch: Name of the branch to branch from. If not provided, defaults to the repository's default branch.
    
    Returns:
        A dictionary with success status and branch information or error details.
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
    """
    Forks a GitHub repository, optionally into a specified organization.
    
    Args:
        owner: The owner of the repository to fork.
        repo: The name of the repository to fork.
        organization: The organization to fork the repository into, if applicable.
    
    Returns:
        A dictionary with the result of the fork operation, including success status and fork details or error information.
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
    """
    Merges a pull request into the specified repository.
    
    Args:
        owner: The username or organization that owns the repository.
        repo: The name of the repository.
        pull_number: The number identifying the pull request to merge.
        commit_title: Optional custom title for the merge commit.
        commit_message: Optional custom message for the merge commit.
        merge_method: The merge strategy to use ("merge", "squash", or "rebase").
    
    Returns:
        A dictionary with "success": True and merge details if successful, or "success": False and an error message if the merge fails.
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