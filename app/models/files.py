from sqlalchemy import Column, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from app.database import Base

class File(Base):
    __tablename__ = "files"

    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id"))
    version_id = Column(UUID(as_uuid=True), ForeignKey("project_versions.version_id"))
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    filename = Column(Text, nullable=False)
    filepath = Column(Text, nullable=False)
    filetype = Column(Text, nullable=False)
    status = Column(Text)
    created_at = Column(TIMESTAMP)
