from sqlalchemy import Column, Text, TIMESTAMP, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from app.database import Base

class Project(Base):
    __tablename__ = "projects"

    project_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    created_at = Column(TIMESTAMP)

class ProjectVersion(Base):
    __tablename__ = "project_versions"

    version_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id"))
    version_number = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(TIMESTAMP)
    is_active = Column(Boolean, default=True)
