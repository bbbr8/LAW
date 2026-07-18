from __future__ import annotations

import hashlib
from typing import Any

import networkx as nx

from .schemas import GraphEdge, GraphNode, PairRelation, SourceAnalysis


def _id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"


def build_graph(analyses: list[SourceAnalysis], relations: list[PairRelation], known_events: list[dict[str, Any]]) -> dict[str, Any]:
    graph = nx.MultiDiGraph()
    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}

    def add_node(node_id: str, node_type: str, label: str, **attrs: Any) -> None:
        if node_id not in nodes:
            nodes[node_id] = GraphNode(node_id=node_id, node_type=node_type, label=label, attributes=attrs)
            graph.add_node(node_id, node_type=node_type, label=label, **attrs)

    def add_edge(source: str, target: str, edge_type: str, **attrs: Any) -> None:
        edge_id = _id("EDGE", f"{source}|{target}|{edge_type}|{len(edges)}")
        edges[edge_id] = GraphEdge(edge_id=edge_id, source=source, target=target, edge_type=edge_type, attributes=attrs)
        graph.add_edge(source, target, key=edge_id, edge_type=edge_type, **attrs)

    for analysis in analyses:
        source_node = f"SRC-{analysis.source_id}"
        add_node(source_node, "SOURCE", analysis.source_id, sha256=analysis.source_sha256, role=analysis.selected_role, path=analysis.path)
        role_node = f"ROLE-{analysis.selected_role}"
        add_node(role_node, "DOCUMENT_ROLE", analysis.selected_role)
        add_edge(source_node, role_node, "HAS_ROLE")
        for item in analysis.extracted_items:
            if item.kind == "amount":
                key = f"{float(item.value):.2f}"
                node_id = _id("AMT", key)
                add_node(node_id, "AMOUNT", f"${key}", value=float(item.value))
                add_edge(source_node, node_id, "MENTIONS_AMOUNT", page=item.page)
            elif item.kind in {"date", "envelope_id", "account_number", "address", "invoice_number_candidate"}:
                node_id = _id(item.kind.upper(), str(item.normalized or item.value))
                add_node(node_id, item.kind.upper(), str(item.value), normalized=item.normalized)
                add_edge(source_node, node_id, f"MENTIONS_{item.kind.upper()}", page=item.page)

    for relation in relations:
        left = f"SRC-{relation.left_source_id}"
        right = f"SRC-{relation.right_source_id}"
        add_edge(left, right, relation.classification.upper(), score=relation.score, promotion_state=relation.promotion_state.value)

    for event in known_events:
        event_id = f"EVT-{event['event_id']}"
        add_node(event_id, "EVENT", event["event_id"], **event)
        if event.get("source_id"):
            add_edge(f"SRC-{event['source_id']}", event_id, "SUPPORTS_EVENT")
        stage_node = f"STAGE-{event['stage']}"
        add_node(stage_node, "LIFECYCLE_STAGE", event["stage"])
        add_edge(event_id, stage_node, "HAS_STAGE")

    return {
        "directed": True,
        "multigraph": True,
        "nodes": [node.model_dump() for node in nodes.values()],
        "edges": [edge.model_dump() for edge in edges.values()],
        "metrics": {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "weak_component_count": nx.number_weakly_connected_components(graph) if graph.number_of_nodes() else 0,
        },
    }
