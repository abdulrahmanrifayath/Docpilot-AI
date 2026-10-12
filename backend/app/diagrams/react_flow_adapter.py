from typing import Any, Dict, List
from pathlib import Path


class ReactFlowAdapter:
    def convert(self, dependency_data: Dict[str, Any], apis: List[Dict[str, Any]], models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Transforms analysis data into React Flow nodes and edges with coordinates and categories.
        """
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # Categorize nodes into columns/layers:
        # Layer 0: Entrypoints / Clients / Routes
        # Layer 1: Services / Business Logic
        # Layer 2: Core / Utils
        # Layer 3: Models / Database
        layers: Dict[int, List[Dict[str, Any]]] = {0: [], 1: [], 2: [], 3: []}

        dep_nodes = dependency_data.get("nodes", [])

        for idx, item in enumerate(dep_nodes[:35]):
            path = item["path"].lower()
            name = item["label"]
            in_deg = item.get("in_degree", 0)
            out_deg = item.get("out_degree", 0)

            if "api" in path or "route" in path or "controller" in path or "view" in path:
                layer_idx = 0
                node_category = "api"
                color = "#06b6d4"  # cyan
            elif "service" in path or "logic" in path or "handler" in path:
                layer_idx = 1
                node_category = "service"
                color = "#10b981"  # emerald
            elif "model" in path or "schema" in path or "db" in path or "entity" in path:
                layer_idx = 3
                node_category = "model"
                color = "#f59e0b"  # amber
            else:
                layer_idx = 2
                node_category = "core"
                color = "#8b5cf6"  # violet

            layers[layer_idx].append({
                "id": item["id"],
                "label": name,
                "path": item["path"],
                "category": node_category,
                "color": color,
                "in_degree": in_deg,
                "out_degree": out_deg,
                "language": item.get("language", ""),
            })

        # Calculate coordinates (x: layer * 320, y: row * 120)
        for layer_idx, layer_nodes in layers.items():
            for row_idx, node_info in enumerate(layer_nodes):
                x = layer_idx * 320 + 80
                y = row_idx * 110 + 60
                nodes.append({
                    "id": node_info["id"],
                    "type": "custom",
                    "position": {"x": x, "y": y},
                    "data": {
                        "label": node_info["label"],
                        "path": node_info["path"],
                        "category": node_info["category"],
                        "color": node_info["color"],
                        "in_degree": node_info["in_degree"],
                        "out_degree": node_info["out_degree"],
                        "language": node_info["language"],
                    },
                })

        # Add edges
        node_id_set = {n["id"] for n in nodes}
        for edge_idx, edge in enumerate(dependency_data.get("edges", [])[:50]):
            src = edge["source"]
            tgt = edge["target"]
            if src in node_id_set and tgt in node_id_set:
                edges.append({
                    "id": f"e-{src}-{tgt}-{edge_idx}",
                    "source": src,
                    "target": tgt,
                    "animated": True,
                    "style": {"stroke": "#94a3b8", "strokeWidth": 2},
                    "label": ", ".join(edge.get("symbols", [])[:2]) if edge.get("symbols") else None,
                })

        return {
            "nodes": nodes,
            "edges": edges,
        }
