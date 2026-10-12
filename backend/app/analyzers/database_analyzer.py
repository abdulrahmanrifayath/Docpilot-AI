from typing import Any, Dict, List
from app.parsers.base import DatabaseModel, ParsedFile


class DatabaseAnalyzer:
    def analyze(self, parsed_files: List[ParsedFile]) -> Dict[str, Any]:
        """Consolidates database models, fields, and relationships across the project."""
        models: List[Dict[str, Any]] = []
        model_names = set()

        for pf in parsed_files:
            for db_model in pf.db_models:
                model_names.add(db_model.name)
                models.append(
                    {
                        "name": db_model.name,
                        "table_name": db_model.table_name or db_model.name.lower(),
                        "source_file": pf.relative_path,
                        "start_line": db_model.start_line,
                        "orm_type": db_model.orm_type,
                        "fields": [f.model_dump() for f in db_model.fields],
                        "relationships": [r.model_dump() for r in db_model.relationships],
                    }
                )

        # Build inter-model relationship links
        cross_model_relations: List[Dict[str, Any]] = []
        for model in models:
            for field in model["fields"]:
                if field.get("is_foreign_key") and field.get("foreign_key_target"):
                    target = field["foreign_key_target"].split(".")[0]
                    # Find matching model name
                    matching_model = next(
                        (m["name"] for m in models if m["table_name"] == target or m["name"].lower() == target.lower()),
                        target.capitalize(),
                    )
                    cross_model_relations.append(
                        {
                            "source_model": model["name"],
                            "target_model": matching_model,
                            "foreign_key_field": field["name"],
                            "type": "many_to_one",
                        }
                    )

            for rel in model["relationships"]:
                cross_model_relations.append(
                    {
                        "source_model": model["name"],
                        "target_model": rel["target_model"],
                        "type": rel["relationship_type"],
                    }
                )

        return {
            "total_models": len(models),
            "models": models,
            "relationships": cross_model_relations,
        }
