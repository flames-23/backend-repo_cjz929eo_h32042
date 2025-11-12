"""
Database Schemas for Work in Taiwan Guide

Each Pydantic model corresponds to a MongoDB collection. The collection
name is the lowercase of the model class name.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class User(BaseModel):
    """Users collection schema"""
    email: str = Field(..., description="Email address")
    password_hash: str = Field(..., description="Password hash (server-generated)")
    name: Optional[str] = Field(None, description="Full name")
    role: str = Field("user", description="Role: user | admin")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences like darkMode, language, etc.")

class Progress(BaseModel):
    """User progress checklist per step"""
    user_id: str = Field(..., description="Reference to user _id as string")
    items: Dict[str, bool] = Field(default_factory=dict, description="Checklist map: stepKey -> completed")

class Step(BaseModel):
    """Guide step content"""
    key: str = Field(..., description="Unique key, e.g., passport, job-search")
    title: str = Field(..., description="Step title")
    description: Optional[str] = Field(None, description="Short description")
    content: str = Field("", description="Rich markdown/HTML content")
    resources: List[Dict[str, str]] = Field(default_factory=list, description="List of {label, url}")
    estimate_days: Optional[int] = Field(None, description="Estimated processing time in days")
    cost_estimate: Optional[str] = Field(None, description="Approximate costs text")
    order: int = Field(0, description="Display order")

class Notification(BaseModel):
    """User notifications and reminders"""
    user_id: str = Field(..., description="Reference to user _id as string")
    type: str = Field(..., description="Type of notification, e.g., deadline, reminder")
    message: str = Field(..., description="Notification text")
    due_date: Optional[str] = Field(None, description="ISO date for reminder")

class RecommendationProfile(BaseModel):
    """Optional profile to tailor recommendations"""
    user_id: str = Field(...)
    profession: Optional[str] = None
    language_level: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
