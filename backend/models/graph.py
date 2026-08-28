import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, ForeignKey
from database import Base
from models.guid import GUID

class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    node_id = Column(String(100), nullable=False)
    label = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False) # social | family | academic | digital | lifestyle | emotion
    val_score = Column(Float, default=50.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False)
    source_node = Column(String(100), nullable=False)
    target_node = Column(String(100), nullable=False)
    relationship_type = Column(String(100), default="influences")
    weight = Column(Float, default=1.0)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
