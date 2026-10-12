from typing import Any, Dict, List, Optional, Set
import networkx as nx


class KnowledgeGraphNode:
    def __init__(
        self,
        node_id: str,
        label: str,
        node_type: str,  # directory, file, class, function, api, model
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        docstring: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.node_id = node_id
        self.label = label
        self.node_type = node_type
        self.file_path = file_path
        self.line_number = line_number
        self.docstring = docstring
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.node_id,
            "label": self.label,
            "type": self.node_type,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "docstring": self.docstring,
            "metadata": self.metadata,
        }


class ProjectKnowledgeGraph:
    def __init__(self) -> None:
        self.graph = nx.DiGraph()
        self.nodes_data: Dict[str, KnowledgeGraphNode] = {}

    def add_node(
        self,
        node_id: str,
        label: str,
        node_type: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        docstring: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeGraphNode:
        node = KnowledgeGraphNode(
            node_id=node_id,
            label=label,
            node_type=node_type,
            file_path=file_path,
            line_number=line_number,
            docstring=docstring,
            metadata=metadata,
        )
        self.nodes_data[node_id] = node
        self.graph.add_node(node_id, **node.to_dict())
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str,  # CONTAINS, IMPORTS, CALLS, EXPOSES, PERSISTS, RELATES_TO
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if source_id in self.nodes_data and target_id in self.nodes_data:
            self.graph.add_edge(source_id, target_id, relation=relation, **(metadata or {}))

    def get_node(self, node_id: str) -> Optional[KnowledgeGraphNode]:
        return self.nodes_data.get(node_id)

    def find_nodes_by_type(self, node_type: str) -> List[KnowledgeGraphNode]:
        return [node for node in self.nodes_data.values() if node.node_type == node_type]

    def search_nodes(self, query: str) -> List[KnowledgeGraphNode]:
        q = query.lower()
        results = []
        for node in self.nodes_data.values():
            if q in node.label.lower() or (node.docstring and q in node.docstring.lower()) or (node.file_path and q in node.file_path.lower()):
                results.append(node)
        return results

    def get_neighbors(self, node_id: str) -> Dict[str, List[Dict[str, Any]]]:
        if node_id not in self.graph:
            return {"predecessors": [], "successors": []}
        
        predecessors = []
        for pred in self.graph.predecessors(node_id):
            edge_data = self.graph.get_edge_data(pred, node_id)
            pred_node = self.nodes_data.get(pred)
            if pred_node:
                predecessors.append({"node": pred_node.to_dict(), "relation": edge_data.get("relation", "LINK")})

        successors = []
        for succ in self.graph.successors(node_id):
            edge_data = self.graph.get_edge_data(node_id, succ)
            succ_node = self.nodes_data.get(succ)
            if succ_node:
                successors.append({"node": succ_node.to_dict(), "relation": edge_data.get("relation", "LINK")})

        return {"predecessors": predecessors, "successors": successors}

    def to_dict(self) -> Dict[str, Any]:
        nodes = [node.to_dict() for node in self.nodes_data.values()]
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append(
                {
                    "source": u,
                    "target": v,
                    "relation": data.get("relation", "CONNECTED_TO"),
                    "metadata": {k: v for k, v in data.items() if k != "relation"},
                }
            )
        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "nodes": nodes,
            "edges": edges,
        }
