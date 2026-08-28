from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models.graph import GraphNode, GraphEdge
import uuid

# Base seed nodes across categories
DEFAULT_NODES = [
    {"node_id": "academic_pressure", "label": "Academic Pressure", "category": "academic", "val_score": 65.0},
    {"node_id": "screen_time", "label": "Late-Night Screen Use", "category": "digital", "val_score": 60.0},
    {"node_id": "sleep_quality", "label": "Sleep Quality & Rest", "category": "lifestyle", "val_score": 55.0},
    {"node_id": "daily_energy", "label": "Energy & Stamina", "category": "lifestyle", "val_score": 50.0},
    {"node_id": "social_connection", "label": "Social Connection", "category": "social", "val_score": 65.0},
    {"node_id": "family_support", "label": "Family Communication", "category": "family", "val_score": 70.0},
    {"node_id": "emotional_state", "label": "Emotional Balance", "category": "emotion", "val_score": 60.0},
]

DEFAULT_EDGES = [
    {"source_node": "academic_pressure", "target_node": "screen_time", "relationship_type": "triggers", "weight": 0.8, "description": "Stress leads to late-night doomscrolling"},
    {"source_node": "screen_time", "target_node": "sleep_quality", "relationship_type": "reduces", "weight": 0.85, "description": "Blue light & late hours disrupt restorative sleep"},
    {"source_node": "sleep_quality", "target_node": "daily_energy", "relationship_type": "depletes", "weight": 0.9, "description": "Sleep deficit leads to daytime fatigue"},
    {"source_node": "daily_energy", "target_node": "emotional_state", "relationship_type": "strains", "weight": 0.75, "description": "Fatigue reduces emotional resilience"},
    {"source_node": "emotional_state", "target_node": "social_connection", "relationship_type": "leads_to_withdrawal", "weight": 0.7, "description": "Low mood prompts social isolation"},
    {"source_node": "family_support", "target_node": "emotional_state", "relationship_type": "supports", "weight": 0.8, "description": "Positive family talks buffer stress"}
]

class GraphManager:
    """
    Manages the Personal Wellbeing Graph structure, calculating node impacts
    and outputting graph topologies formatted for React Flow.
    """

    @classmethod
    def get_or_initialize_graph(cls, db: Session, user_id) -> Dict[str, Any]:
        """
        Retrieves graph nodes and edges for a user, initializing default seed graph if empty.
        """
        nodes = db.query(GraphNode).filter(GraphNode.user_id == user_id).all()
        edges = db.query(GraphEdge).filter(GraphEdge.user_id == user_id).all()

        if not nodes:
            # Seed graph
            for nd in DEFAULT_NODES:
                db_node = GraphNode(
                    user_id=user_id,
                    node_id=nd["node_id"],
                    label=nd["label"],
                    category=nd["category"],
                    val_score=nd["val_score"]
                )
                db.add(db_node)

            for eg in DEFAULT_EDGES:
                db_edge = GraphEdge(
                    user_id=user_id,
                    source_node=eg["source_node"],
                    target_node=eg["target_node"],
                    relationship_type=eg["relationship_type"],
                    weight=eg["weight"],
                    description=eg["description"]
                )
                db.add(db_edge)

            db.commit()
            nodes = db.query(GraphNode).filter(GraphNode.user_id == user_id).all()
            edges = db.query(GraphEdge).filter(GraphEdge.user_id == user_id).all()

        return cls.format_for_react_flow(nodes, edges)

    @classmethod
    def update_graph_from_patterns(
        cls,
        db: Session,
        user_id,
        patterns: List[Dict[str, Any]],
        dimension_scores: Dict[str, float]
    ):
        """
        Dynamically adjusts node scores and edge weights based on newly detected patterns.
        """
        # Update node scores based on latest dimension balances
        dim_map = {
            "academic": "academic_pressure",
            "digital": "screen_time",
            "lifestyle": "sleep_quality",
            "social": "social_connection",
            "family": "family_support"
        }

        for dim, node_id in dim_map.items():
            if dim in dimension_scores:
                node = db.query(GraphNode).filter(GraphNode.user_id == user_id, GraphNode.node_id == node_id).first()
                if node:
                    # Invert score for negative concepts like pressure / screen time
                    if node_id in ["academic_pressure", "screen_time"]:
                        node.val_score = round(100.0 - dimension_scores[dim], 1)
                    else:
                        node.val_score = round(dimension_scores[dim], 1)

        # Strengthen edges if patterns reinforce them
        for pattern in patterns:
            dims = pattern.get("dimensions_involved", [])
            if "academic" in dims and "digital" in dims:
                edge = db.query(GraphEdge).filter(
                    GraphEdge.user_id == user_id,
                    GraphEdge.source_node == "academic_pressure",
                    GraphEdge.target_node == "screen_time"
                ).first()
                if edge:
                    edge.weight = min(1.0, edge.weight + 0.05)

            if "lifestyle" in dims and "social" in dims:
                edge = db.query(GraphEdge).filter(
                    GraphEdge.user_id == user_id,
                    GraphEdge.source_node == "emotional_state",
                    GraphEdge.target_node == "social_connection"
                ).first()
                if edge:
                    edge.weight = min(1.0, edge.weight + 0.05)

        db.commit()

    @classmethod
    def format_for_react_flow(cls, nodes: List[GraphNode], edges: List[GraphEdge]) -> Dict[str, Any]:
        """
        Formats graph for React Flow visualization component.
        """
        # Node category color map
        category_colors = {
            "academic": {"bg": "rgba(239, 68, 68, 0.15)", "border": "#ef4444", "text": "#fca5a5"},
            "digital": {"bg": "rgba(249, 115, 22, 0.15)", "border": "#f97316", "text": "#fdba74"},
            "lifestyle": {"bg": "rgba(16, 185, 129, 0.15)", "border": "#10b981", "text": "#6ee7b7"},
            "social": {"bg": "rgba(59, 130, 246, 0.15)", "border": "#3b82f6", "text": "#93c5fd"},
            "family": {"bg": "rgba(168, 85, 247, 0.15)", "border": "#a855f7", "text": "#d8b4fe"},
            "emotion": {"bg": "rgba(236, 72, 153, 0.15)", "border": "#ec4899", "text": "#f472b6"}
        }

        # Preset layout positions
        positions = {
            "academic_pressure": {"x": 50, "y": 80},
            "screen_time": {"x": 300, "y": 80},
            "sleep_quality": {"x": 550, "y": 80},
            "daily_energy": {"x": 550, "y": 260},
            "emotional_state": {"x": 300, "y": 260},
            "social_connection": {"x": 50, "y": 260},
            "family_support": {"x": 300, "y": 420},
        }

        flow_nodes = []
        for i, n in enumerate(nodes):
            pos = positions.get(n.node_id, {"x": 100 + (i % 3) * 220, "y": 100 + (i // 3) * 160})
            style = category_colors.get(n.category, category_colors["academic"])

            flow_nodes.append({
                "id": n.node_id,
                "type": "wellbeingNode",
                "position": pos,
                "data": {
                    "label": n.label,
                    "category": n.category,
                    "val_score": n.val_score,
                    "colorStyle": style
                }
            })

        flow_edges = []
        for eg in edges:
            flow_edges.append({
                "id": f"{eg.source_node}-{eg.target_node}",
                "source": eg.source_node,
                "target": eg.target_node,
                "animated": eg.weight >= 0.75,
                "label": eg.relationship_type.replace("_", " "),
                "style": {
                    "stroke": "#818cf8" if eg.weight < 0.8 else "#f43f5e",
                    "strokeWidth": max(1.5, eg.weight * 3.5),
                    "opacity": max(0.6, eg.weight)
                },
                "data": {
                    "weight": eg.weight,
                    "description": eg.description
                }
            })

        return {"nodes": flow_nodes, "edges": flow_edges}
