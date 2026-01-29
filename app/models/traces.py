from sqlalchemy import Column, Text, TIMESTAMP, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from app.database import Base

class Trace(Base):
    __tablename__ = "traces"

    trace_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    similarity = Column(Float)
    embedding_id = Column(Text, nullable=False)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.chunk_id"))
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.file_id"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id"))
    version_id = Column(UUID(as_uuid=True), ForeignKey("project_versions.version_id"))
    created_at = Column(TIMESTAMP)
