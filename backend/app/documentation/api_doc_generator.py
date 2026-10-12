from typing import Any, Dict, List


class ApiDocGenerator:
    def generate(self, api_analysis: Dict[str, Any], repo_name: str) -> str:
        """Generates comprehensive REST API documentation."""
        grouped = api_analysis.get("grouped_by_tag", {})
        total = api_analysis.get("total_endpoints", 0)
        auth_count = api_analysis.get("authenticated_count", 0)
        method_dist = api_analysis.get("method_distribution", {})

        methods_summary = " ".join([f"`{m}: {c}`" for m, c in method_dist.items()]) or "`None detected`"

        sections = [
            f"# {repo_name} — API Reference Documentation",
            "",
            "> Complete endpoint definitions, parameter schemas, and request lifecycles.",
            "",
            "## 📊 API Overview",
            f"- **Total Endpoints**: `{total}`",
            f"- **Authenticated Endpoints**: `{auth_count}`",
            f"- **Public Endpoints**: `{total - auth_count}`",
            f"- **HTTP Methods**: {methods_summary}",
            "",
            "---",
            "",
        ]

        if not grouped:
            sections.append("No explicit REST API routes were identified during static code analysis.")
            return "\n".join(sections)

        for tag, endpoints in grouped.items():
            sections.append(f"## 🏷️ {tag} Endpoints\n")
            for ep in endpoints:
                method = ep.get("method", "GET")
                path = ep.get("path", "/")
                auth = "🔒 Requires Authentication" if ep.get("auth_required") else "🌐 Public Endpoint"
                doc = ep.get("docstring") or "No explicit docstring provided."
                params = ep.get("parameters", [])
                resp = ep.get("response_model") or "Standard JSON Response"
                src = f"`{ep.get('source_file')}:{ep.get('line_number')}`"

                sections.extend([
                    f"### `{method}` `{path}`",
                    "",
                    f"**Status**: {auth}  ",
                    f"**Defined in**: {src}  ",
                    f"**Handler**: `{ep.get('handler_name')}`",
                    "",
                    f"**Description**:\n> {doc.strip()}",
                    "",
                ])

                # Parameters table
                if params:
                    sections.append("#### Parameters\n")
                    sections.append("| Name | Type | In | Description |")
                    sections.append("|:---|:---|:---|:---|")
                    for p in params:
                        sections.append(f"| `{p.get('name')}` | `{p.get('type', 'string')}` | Query/Path | Parameter value |")
                    sections.append("")

                # Response
                sections.extend([
                    "#### Expected Response",
                    f"- **Schema**: `{resp}`",
                    "",
                    "#### Example Request",
                    "```bash",
                    f"curl -X {method} 'http://localhost:8000{path}' \\",
                    "  -H 'Content-Type: application/json'",
                    "```",
                    "",
                    "---",
                    "",
                ])

        return "\n".join(sections)
