from typing import Any, Dict, List
from collections import defaultdict
from app.parsers.base import APIEndpoint, ParsedFile


class APIAnalyzer:
    def analyze(self, parsed_files: List[ParsedFile]) -> Dict[str, Any]:
        """Consolidates and categorizes all detected API endpoints."""
        all_endpoints: List[Dict[str, Any]] = []
        method_counts: Dict[str, int] = defaultdict(int)
        grouped_by_tag: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        auth_count = 0

        for pf in parsed_files:
            for api in pf.apis:
                method = api.method.upper()
                method_counts[method] += 1
                if api.auth_required:
                    auth_count += 1

                # Group by first segment of path (e.g. /api/users -> users)
                path_segments = [s for s in api.path.strip("/").split("/") if s and s not in ("api", "v1", "v2")]
                tag = path_segments[0].capitalize() if path_segments else "Root"

                ep_data = {
                    "method": method,
                    "path": api.path,
                    "handler_name": api.handler_name,
                    "source_file": pf.relative_path,
                    "line_number": api.start_line,
                    "docstring": api.docstring,
                    "parameters": api.parameters,
                    "response_model": api.response_model,
                    "auth_required": api.auth_required,
                    "framework": api.framework,
                    "tag": tag,
                }
                all_endpoints.append(ep_data)
                grouped_by_tag[tag].append(ep_data)

        # Sort all endpoints by path
        all_endpoints.sort(key=lambda x: (x["path"], x["method"]))

        return {
            "total_endpoints": len(all_endpoints),
            "authenticated_count": auth_count,
            "public_count": len(all_endpoints) - auth_count,
            "method_distribution": dict(method_counts),
            "endpoints": all_endpoints,
            "grouped_by_tag": dict(grouped_by_tag),
        }
