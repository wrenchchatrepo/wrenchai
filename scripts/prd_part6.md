### 5.3 Playbook Configuration Model

```python
# models/playbook_config.py
"""Pydantic models for playbook configuration."""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum

class ThemeType(str, Enum):
    """Theme options for Docusaurus."""
    CLASSIC = "classic"
    MODERN = "modern"
    MINIMAL = "minimal"
    DARK = "dark"

class Technology(str, Enum):
    """Common technology options."""
    PYTHON = "Python"
    JAVASCRIPT = "JavaScript"
    TYPESCRIPT = "TypeScript"
    REACT = "React"
    NEXTJS = "Next.js"
    FASTAPI = "FastAPI"
    DJANGO = "Django"
    DOCKER = "Docker"
    KUBERNETES = "Kubernetes"
    AWS = "AWS"
    GCP = "Google Cloud"
    AZURE = "Azure"
    PYTORCH = "PyTorch"
    TENSORFLOW = "TensorFlow"
    SCIKIT_LEARN = "Scikit-learn"
    SQL = "SQL"
    NOSQL = "NoSQL"

class Project(BaseModel):
    """Project configuration for portfolio."""
    name: str = Field(..., 
                      description="Name of the project",
                      min_length=3, 
                      max_length=100)
    description: str = Field(..., 
                           description="Brief description of the project",
                           min_length=10, 
                           max_length=500)
    github_url: Optional[str] = Field(None, 
                                     description="GitHub repository URL")
    technologies: List[Technology] = Field(default_factory=list,
                                          description="Technologies used in the project")
    image_url: Optional[str] = Field(None,
                                    description="URL to project image or screenshot")

class SocialLinks(BaseModel):
    """Social media links configuration."""
    github: Optional[str] = Field(None, description="GitHub username")
    linkedin: Optional[str] = Field(None, description="LinkedIn URL or username")
    twitter: Optional[str] = Field(None, description="Twitter/X username")
    personal_website: Optional[str] = Field(None, description="Personal website URL")
    email: Optional[str] = Field(None, description="Public email address")

class DocusaurusConfig(BaseModel):
    """Configuration for Docusaurus portfolio."""
    title: str = Field(..., 
                      description="Portfolio title",
                      min_length=3, 
                      max_length=100)
    description: str = Field(..., 
                           description="Portfolio description",
                           min_length=10, 
                           max_length=500)
    theme: ThemeType = Field(default=ThemeType.MODERN, 
                           description="Visual theme for the portfolio")
    projects: List[Project] = Field(default_factory=list,
                                   description="Projects to include in the portfolio")
    custom_domain: Optional[str] = Field(None, 
                                        description="Custom domain for deployment")
    analytics_id: Optional[str] = Field(None, 
                                       description="Google Analytics ID")
    social_links: SocialLinks = Field(default_factory=SocialLinks, 
                                     description="Social media links")

    class Config:
        schema_extra = {
            "example": {
                "title": "Jane Doe's Developer Portfolio",
                "description": "A showcase of my software development projects and skills",
                "theme": "modern",
                "projects": [
                    {
                        "name": "AI Chat Application",
                        "description": "A real-time chat application powered by AI",
                        "github_url": "https://github.com/janedoe/ai-chat",
                        "technologies": ["Python", "FastAPI", "React", "PyTorch"]
                    }
                ],
                "custom_domain": "portfolio.janedoe.com",
                "social_links": {
                    "github": "janedoe",
                    "linkedin": "jane-doe",
                    "twitter": "jane_doe_dev"
                }
            }
        }
```