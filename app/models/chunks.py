from sqlalchemy import Column, Text, TIMESTAMP, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from app.database import Base

class Chunk(Base):
    __tablename__ = "chunks"

    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    doc_id = Column(UUID(as_uuid=True), ForeignKey("parsed_documents.doc_id"))
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.file_id"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id"))
    version_id = Column(UUID(as_uuid=True), ForeignKey("project_versions.version_id"))
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(Text)
    created_at = Column(TIMESTAMP)
