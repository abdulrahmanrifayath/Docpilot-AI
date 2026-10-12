from typing import Any, Dict, List


class ReportGenerator:
    def generate(
        self,
        repo_name: str,
        stats: Dict[str, Any],
        languages: Dict[str, Any],
        dependency_analysis: Dict[str, Any],
        api_analysis: Dict[str, Any],
        database_analysis: Dict[str, Any],
    ) -> str:
        """Generates an automated Technical Architecture and Health Report."""
        files = stats.get("files", 0)
        lines = stats.get("lines", 0)
        classes = stats.get("classes", 0)
        functions = stats.get("functions", 0)
        apis = api_analysis.get("total_endpoints", 0)
        models = database_analysis.get("total_models", 0)
        has_cycles = dependency_analysis.get("has_circular_dependencies", False)

        # Health score calculation
        score = 90
        if has_cycles:
            score -= 15
        if files > 0 and (lines / files) > 400:
            score -= 10
        if apis > 0 and api_analysis.get("authenticated_count", 0) == 0:
            score -= 10
        score = max(score, 50)

        grade = "A" if score >= 85 else ("B" if score >= 70 else "C")

        avg_lines = round(lines / files, 1) if files > 0 else 0
        avg_funcs = round(functions / files, 1) if files > 0 else 0

        recommendations = []
        if has_cycles:
            recommendations.append("- **Decouple circular dependencies**: Break cycles identified in module dependency analysis by introducing interface abstractions or event dispatchers.")
        if avg_lines > 300:
            recommendations.append("- **Decompose large modules**: Several modules exceed 300 lines of code; consider extracting sub-services.")
        if apis > 0 and api_analysis.get("authenticated_count", 0) == 0:
            recommendations.append("- **Review API Authentication**: All detected endpoints appear public; verify if authentication guards are required.")
        if not recommendations:
            recommendations.append("- **Maintain high code standards**: Module organization and separation of concerns are well aligned.")

        return f"""# 📈 {repo_name} — Technical Health & Architecture Report

> Quantitative code metrics, maintainability grading, and architectural risk assessment.

---

## 🏆 Overall Maintainability Grade: **{grade} ({score}/100)**

| Metric Category | Assessment | Status |
|:---|:---|:---|
| **Module Modularity** | {f"⚠️ {len(dependency_analysis.get('circular_dependencies', []))} circular cycles" if has_cycles else "✅ Decoupled module hierarchy"} | {"Warning" if has_cycles else "Healthy"} |
| **File Sizing** | Average `{avg_lines}` lines / file | {"Good" if avg_lines < 300 else "Needs attention"} |
| **API Exposure** | `{apis}` endpoints (`{api_analysis.get('authenticated_count', 0)}` secured) | {"Healthy" if api_analysis.get('authenticated_count', 0) > 0 or apis == 0 else "Review"} |
| **Data Schema Depth** | `{models}` database entities modeled | Informational |

---

## 📊 Quantitative Metrics

| Metric | Measured Value | Benchmark |
|:---|:---|:---|
| Total Source Files | `{files:,}` | — |
| Total Lines of Code | `{lines:,}` | — |
| Total Classes | `{classes:,}` | — |
| Total Functions | `{functions:,}` | ~`{avg_funcs}` per file |
| Total REST Endpoints | `{apis}` | — |
| Total Database Models | `{models}` | — |
| External Package Dependencies | `{len(dependency_analysis.get('external_dependencies', []))}` | Monitored |

---

## 🌐 Language Composition

| Language | Files Count | Code Lines | Share |
|:---|:---|:---|:---|
{chr(10).join([f"| `{lang}` | `{data.get('files')}` | `{data.get('lines'):,}` | `{data.get('percent')}%` |" for lang, data in languages.items()])}

---

## 💡 Actionable Engineering Recommendations

{chr(10).join(recommendations)}

---
*Report generated automatically by DocPilot AI static intelligence pipeline.*
"""
