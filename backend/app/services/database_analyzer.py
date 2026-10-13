import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class StaticDatabaseStructureAnalyzer:
    """
    Statically analyzes source code to extract database models, fields, and relationships.
    Supports:
    - SQLAlchemy (Classic & SQLAlchemy 2.0 / mapped_column / SQLModel)
    - Django ORM
    - Raw SQL schema files (.sql)
    """

    IGNORE_DIRS = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".pytest_cache",
        "coverage",
        ".mypy_cache",
        ".idea",
        ".vscode",
    }

    def analyze_repository(self, project_root: str) -> Dict[str, Any]:
        """
        Recursively scans the project directory and returns database models, fields, and relationships.
        Does not execute SQL or connect to any database.
        """
        root_path = Path(project_root)
        if not root_path.exists() or not root_path.is_dir():
            return {
                "models": [],
                "relationships": [],
                "orm_breakdown": {},
            }

        discovered_models: List[Dict[str, Any]] = []
        raw_relationships: List[Dict[str, Any]] = []

        for dirpath, dirnames, filenames in os.walk(str(root_path)):
            dirnames[:] = [d for d in dirnames if d not in self.IGNORE_DIRS and not d.startswith(".")]

            for filename in filenames:
                file_path = Path(dirpath) / filename
                rel_path = file_path.relative_to(root_path).as_posix()

                if filename.endswith(".py"):
                    models, rels = self._parse_python_models(file_path, rel_path)
                    discovered_models.extend(models)
                    raw_relationships.extend(rels)
                elif filename.endswith(".sql"):
                    models, rels = self._parse_sql_file(file_path, rel_path)
                    discovered_models.extend(models)
                    raw_relationships.extend(rels)

        # Deduplicate models by table_name or name
        unique_models: List[Dict[str, Any]] = []
        seen_tables = set()
        for m in discovered_models:
            key = (m["name"], m["table_name"])
            if key not in seen_tables:
                seen_tables.add(key)
                unique_models.append(m)

        # Resolve cross-model relationships (foreign keys & ORM links)
        relationships = self._resolve_relationships(unique_models, raw_relationships)

        # ORM Breakdown
        orm_breakdown: Dict[str, int] = {}
        for m in unique_models:
            orm = m.get("orm_type", "SQLAlchemy")
            orm_breakdown[orm] = orm_breakdown.get(orm, 0) + 1

        return {
            "models": unique_models,
            "relationships": relationships,
            "orm_breakdown": orm_breakdown,
        }

    # =========================================================================
    # PYTHON: SQLAlchemy & Django ORM
    # =========================================================================

    def _parse_python_models(
        self, file_path: Path, rel_path: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(file_path))
        except Exception:
            return [], []

        models: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                model_data, model_rels = self._extract_python_class_model(node, rel_path)
                if model_data:
                    models.append(model_data)
                    relationships.extend(model_rels)

        return models, relationships

    def _extract_python_class_model(
        self, node: ast.ClassDef, rel_path: str
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        base_names = [self._format_node(base) for base in node.bases]
        class_name = node.name

        # Check ORM base inheritance or traits
        is_sqlalchemy_base = any(
            b in {"Base", "db.Model", "DeclarativeBase", "Model", "SQLModel"} or "Base" in b
            for b in base_names
        )
        is_django_base = any(
            b in {"models.Model", "Model"} or "Model" in b
            for b in base_names
        )

        # Inspect class attributes
        table_name = None
        fields: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []
        has_orm_attributes = False

        for item in node.body:
            # 1. __tablename__ = 'users'
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                            table_name = item.value.value
                            has_orm_attributes = True

            # 2. Django Meta: class Meta: db_table = 'app_users'
            if isinstance(item, ast.ClassDef) and item.name == "Meta":
                for meta_item in item.body:
                    if isinstance(meta_item, ast.Assign):
                        for target in meta_item.targets:
                            if isinstance(target, ast.Name) and target.id == "db_table":
                                if isinstance(meta_item.value, ast.Constant) and isinstance(meta_item.value.value, str):
                                    table_name = meta_item.value.value
                                    is_django_base = True

            # 3. Classic SQLAlchemy Column(...) or relationship(...) or Django Field(...)
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith("__"):
                        attr_name = target.id
                        val = item.value

                        # SQLAlchemy relationship(...)
                        if isinstance(val, ast.Call) and "relationship" in self._format_node(val.func):
                            rel = self._extract_sqlalchemy_relationship(class_name, attr_name, val)
                            if rel:
                                relationships.append(rel)
                                has_orm_attributes = True
                            continue

                        # SQLAlchemy Column(...)
                        if isinstance(val, ast.Call) and "Column" in self._format_node(val.func):
                            field = self._extract_sqlalchemy_column(attr_name, val)
                            if field:
                                fields.append(field)
                                has_orm_attributes = True
                            continue

                        # Django models.XField(...)
                        call_func = self._format_node(val.func) if isinstance(val, ast.Call) else ""
                        if "models." in call_func or any(
                            f in call_func for f in ["CharField", "IntegerField", "ForeignKey", "OneToOneField", "ManyToManyField"]
                        ):
                            field, rel = self._extract_django_field(class_name, attr_name, val)
                            if field:
                                fields.append(field)
                                has_orm_attributes = True
                            if rel:
                                relationships.append(rel)
                                has_orm_attributes = True
                            continue

            # 4. SQLAlchemy 2.0 mapped_column(...) or Annotated/Mapped fields
            if isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name) and not item.target.id.startswith("__"):
                    attr_name = item.target.id
                    field, rel = self._extract_sqlalchemy2_annassign(class_name, attr_name, item)
                    if field:
                        fields.append(field)
                        has_orm_attributes = True
                    if rel:
                        relationships.append(rel)
                        has_orm_attributes = True

        if not (is_sqlalchemy_base or is_django_base or has_orm_attributes or table_name):
            return None, []

        # If fields are empty and no table_name, skip non-models
        if not fields and not table_name:
            return None, []

        # Derive table name if not explicitly declared
        if not table_name:
            table_name = self._pluralize(class_name.lower())

        orm_type = "Django" if is_django_base and not is_sqlalchemy_base else "SQLAlchemy"

        docstring = ast.get_docstring(node)
        metadata = {
            "bases": base_names,
            "docstring": docstring,
            "fields_count": len(fields),
        }

        model_dict = {
            "name": class_name,
            "table_name": table_name,
            "file_path": rel_path,
            "orm_type": orm_type,
            "start_line": node.lineno,
            "fields": fields,
            "metadata": metadata,
        }

        return model_dict, relationships

    # --- SQLAlchemy Extractors ---

    def _extract_sqlalchemy_column(self, col_name: str, call_node: ast.Call) -> Optional[Dict[str, Any]]:
        data_type = "String"
        is_pk = False
        is_fk = False
        fk_target = None
        is_nullable = True
        default_val = None

        # Check positional args: Column(Integer, ForeignKey('users.id'), ...)
        for idx, arg in enumerate(call_node.args):
            arg_str = self._format_node(arg)
            if idx == 0 and isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                # Column("custom_name", Integer)
                col_name = arg.value
            elif "ForeignKey" in arg_str:
                is_fk = True
                fk_target = self._extract_fk_target(arg)
            elif idx < 2:
                data_type = self._clean_data_type(arg_str)

        # Check keyword args
        for kw in call_node.keywords:
            if kw.arg == "primary_key" and self._is_truthy(kw.value):
                is_pk = True
                is_nullable = False
            elif kw.arg == "nullable":
                is_nullable = self._is_truthy(kw.value)
            elif kw.arg == "default":
                default_val = self._format_node(kw.value)
            elif kw.arg == "type_":
                data_type = self._clean_data_type(self._format_node(kw.value))

        return {
            "name": col_name,
            "data_type": data_type,
            "is_primary_key": is_pk,
            "is_foreign_key": is_fk,
            "foreign_key_target": fk_target,
            "is_nullable": is_nullable,
            "default_value": default_val,
            "metadata": {},
        }

    def _extract_sqlalchemy2_annassign(
        self, model_name: str, col_name: str, node: ast.AnnAssign
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Handles SQLAlchemy 2.0 Mapped[T] = mapped_column(...) or relationship(...)"""
        type_str = self._format_node(node.annotation)
        val = node.value

        # Check relationship
        if val and isinstance(val, ast.Call) and "relationship" in self._format_node(val.func):
            rel = self._extract_sqlalchemy_relationship(model_name, col_name, val)
            return None, rel

        data_type = "String"
        is_pk = False
        is_fk = False
        fk_target = None
        is_nullable = "Optional" in type_str or "None" in type_str
        default_val = None

        # Extract data type from annotation: Mapped[int] -> Integer, Mapped[str] -> String
        if "Mapped[" in type_str:
            inner_type = re.search(r"Mapped\[(.*)\]", type_str)
            if inner_type:
                raw_inner = inner_type.group(1).replace("Optional[", "").replace("]", "").strip()
                data_type = self._python_type_to_sql(raw_inner)

        # Inspect mapped_column call if present
        if val and isinstance(val, ast.Call) and "mapped_column" in self._format_node(val.func):
            for arg in val.args:
                arg_str = self._format_node(arg)
                if "ForeignKey" in arg_str:
                    is_fk = True
                    fk_target = self._extract_fk_target(arg)
                else:
                    data_type = self._clean_data_type(arg_str)

            for kw in val.keywords:
                if kw.arg == "primary_key" and self._is_truthy(kw.value):
                    is_pk = True
                    is_nullable = False
                elif kw.arg == "nullable":
                    is_nullable = self._is_truthy(kw.value)
                elif kw.arg == "default":
                    default_val = self._format_node(kw.value)

        field = {
            "name": col_name,
            "data_type": data_type,
            "is_primary_key": is_pk,
            "is_foreign_key": is_fk,
            "foreign_key_target": fk_target,
            "is_nullable": is_nullable,
            "default_value": default_val,
            "metadata": {},
        }
        return field, None

    def _extract_sqlalchemy_relationship(
        self, source_model: str, rel_name: str, call_node: ast.Call
    ) -> Optional[Dict[str, Any]]:
        target_model = None
        back_populates = None
        secondary_table = None
        uselist = True

        if call_node.args:
            target_model = self._format_node(call_node.args[0]).strip("'\"")

        for kw in call_node.keywords:
            if kw.arg in ("back_populates", "backref"):
                back_populates = self._format_node(kw.value).strip("'\"")
            elif kw.arg == "secondary":
                secondary_table = self._format_node(kw.value).strip("'\"")
            elif kw.arg == "uselist":
                uselist = self._is_truthy(kw.value)
            elif kw.arg == "target":
                target_model = self._format_node(kw.value).strip("'\"")

        if not target_model:
            return None

        # Clean target model if string or class
        target_model = target_model.split(".")[-1].strip("'\"")

        if secondary_table:
            rel_type = "MANY_TO_MANY"
            desc = "references"
        elif not uselist:
            rel_type = "ONE_TO_ONE"
            desc = "belongs_to"
        else:
            rel_type = "ONE_TO_MANY"
            desc = "has_many"

        return {
            "source_model": source_model,
            "target_model": target_model,
            "relationship_type": rel_type,
            "back_populates": back_populates,
            "secondary_table": secondary_table,
            "description": desc,
            "metadata": {"attribute": rel_name},
        }

    # --- Django Extractors ---

    def _extract_django_field(
        self, model_name: str, field_name: str, call_node: ast.Call
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        func_str = self._format_node(call_node.func).split(".")[-1]
        data_type = func_str.replace("Field", "")
        is_pk = False
        is_fk = False
        fk_target = None
        is_nullable = False
        default_val = None

        relationship = None

        # Check relationship fields in Django
        if func_str == "ForeignKey":
            is_fk = True
            target = self._format_node(call_node.args[0]).strip("'\"") if call_node.args else "Target"
            fk_target = f"{target.lower()}s.id"
            related_name = None
            for kw in call_node.keywords:
                if kw.arg == "related_name":
                    related_name = self._format_node(kw.value).strip("'\"")

            relationship = {
                "source_model": target,
                "target_model": model_name,
                "relationship_type": "ONE_TO_MANY",
                "foreign_key_field": field_name,
                "back_populates": related_name,
                "description": "has_many",
                "metadata": {"django_field": field_name},
            }
            data_type = "Integer"
        elif func_str == "OneToOneField":
            is_fk = True
            target = self._format_node(call_node.args[0]).strip("'\"") if call_node.args else "Target"
            fk_target = f"{target.lower()}s.id"
            relationship = {
                "source_model": target,
                "target_model": model_name,
                "relationship_type": "ONE_TO_ONE",
                "foreign_key_field": field_name,
                "description": "has_one",
                "metadata": {"django_field": field_name},
            }
            data_type = "Integer"
        elif func_str == "ManyToManyField":
            target = self._format_node(call_node.args[0]).strip("'\"") if call_node.args else "Target"
            relationship = {
                "source_model": model_name,
                "target_model": target,
                "relationship_type": "MANY_TO_MANY",
                "description": "references",
                "metadata": {"django_field": field_name},
            }
            return None, relationship

        # Check options: null=True, primary_key=True, default=...
        for kw in call_node.keywords:
            if kw.arg == "primary_key" and self._is_truthy(kw.value):
                is_pk = True
                is_nullable = False
            elif kw.arg == "null":
                is_nullable = self._is_truthy(kw.value)
            elif kw.arg == "default":
                default_val = self._format_node(kw.value)

        field = {
            "name": field_name,
            "data_type": data_type or "String",
            "is_primary_key": is_pk,
            "is_foreign_key": is_fk,
            "foreign_key_target": fk_target,
            "is_nullable": is_nullable,
            "default_value": default_val,
            "metadata": {},
        }
        return field, relationship

    # =========================================================================
    # RAW SQL SCHEMA PARSER (.sql)
    # =========================================================================

    def _parse_sql_file(
        self, file_path: Path, rel_path: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        try:
            sql_content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return [], []

        models: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []

        # Find CREATE TABLE [IF NOT EXISTS] table_name (...)
        table_pattern = re.compile(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"'a-zA-Z0-9_.]+)\s*\(([\s\S]*?)\);",
            re.IGNORECASE,
        )

        for match in table_pattern.finditer(sql_content):
            raw_table_name = match.group(1).strip("`\"' ")
            table_name = raw_table_name.split(".")[-1]
            body_text = match.group(2)

            class_name = self._table_to_class_name(table_name)
            fields: List[Dict[str, Any]] = []

            # Line number
            start_line = sql_content[: match.start()].count("\n") + 1

            # Split columns by comma, respecting parentheses
            col_definitions = self._split_sql_column_lines(body_text)

            for col_def in col_definitions:
                col_def = col_def.strip()
                if not col_def:
                    continue

                # Table-level constraints
                pk_table_match = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", col_def, re.IGNORECASE)
                if pk_table_match and col_def.upper().startswith("PRIMARY"):
                    pk_cols = [c.strip("`\"' ") for c in pk_table_match.group(1).split(",")]
                    for f in fields:
                        if f["name"] in pk_cols:
                            f["is_primary_key"] = True
                            f["is_nullable"] = False
                    continue

                fk_table_match = re.search(
                    r"FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+([`\"'a-zA-Z0-9_.]+)\s*\(([^)]+)\)",
                    col_def,
                    re.IGNORECASE,
                )
                if fk_table_match:
                    local_col = fk_table_match.group(1).strip("`\"' ")
                    ref_table = fk_table_match.group(2).strip("`\"' ").split(".")[-1]
                    ref_col = fk_table_match.group(3).strip("`\"' ")

                    for f in fields:
                        if f["name"] == local_col:
                            f["is_foreign_key"] = True
                            f["foreign_key_target"] = f"{ref_table}.{ref_col}"

                    relationships.append({
                        "source_model": self._table_to_class_name(ref_table),
                        "target_model": class_name,
                        "relationship_type": "FOREIGN_KEY",
                        "foreign_key_field": local_col,
                        "description": "references",
                        "metadata": {"raw_sql": True},
                    })
                    continue

                # Column line: e.g. "id INT PRIMARY KEY AUTO_INCREMENT" or "email VARCHAR(255) NOT NULL"
                tokens = col_def.split()
                if len(tokens) >= 2:
                    col_name = tokens[0].strip("`\"' ")
                    if col_name.upper() in ("CONSTRAINT", "KEY", "INDEX", "UNIQUE", "CHECK"):
                        continue

                    col_type = tokens[1].upper()
                    is_pk = "PRIMARY KEY" in col_def.upper()
                    is_not_null = "NOT NULL" in col_def.upper()
                    is_nullable = not is_not_null and not is_pk

                    is_fk = False
                    fk_target = None
                    inline_fk = re.search(r"REFERENCES\s+([`\"'a-zA-Z0-9_.]+)\s*\(([^)]+)\)", col_def, re.IGNORECASE)
                    if inline_fk:
                        is_fk = True
                        target_tbl = inline_fk.group(1).strip("`\"' ").split(".")[-1]
                        target_c = inline_fk.group(2).strip("`\"' ")
                        fk_target = f"{target_tbl}.{target_c}"

                        relationships.append({
                            "source_model": self._table_to_class_name(target_tbl),
                            "target_model": class_name,
                            "relationship_type": "FOREIGN_KEY",
                            "foreign_key_field": col_name,
                            "description": "references",
                            "metadata": {"raw_sql": True},
                        })

                    fields.append({
                        "name": col_name,
                        "data_type": col_type,
                        "is_primary_key": is_pk,
                        "is_foreign_key": is_fk,
                        "foreign_key_target": fk_target,
                        "is_nullable": is_nullable,
                        "default_value": None,
                        "metadata": {},
                    })

            if fields:
                models.append({
                    "name": class_name,
                    "table_name": table_name,
                    "file_path": rel_path,
                    "orm_type": "SQL",
                    "start_line": start_line,
                    "fields": fields,
                    "metadata": {"raw_sql": True},
                })

        return models, relationships

    # =========================================================================
    # RELATIONSHIP RESOLVER & MERMAID DIAGRAM
    # =========================================================================

    def _resolve_relationships(
        self, models: List[Dict[str, Any]], raw_relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Unifies and normalizes relationships across all models and foreign keys.
        """
        models_by_name = {m["name"]: m for m in models}
        models_by_table = {m["table_name"]: m for m in models}

        relationships: List[Dict[str, Any]] = []
        seen_rels = set()

        # 1. Process explicit ORM relationships
        for rel in raw_relationships:
            src = rel["source_model"]
            tgt = rel["target_model"]

            # Map table names to model names if necessary
            if src in models_by_table:
                src = models_by_table[src]["name"]
            if tgt in models_by_table:
                tgt = models_by_table[tgt]["name"]

            key = (src, tgt, rel["relationship_type"], rel.get("foreign_key_field"))
            if key not in seen_rels:
                seen_rels.add(key)
                relationships.append({
                    "source_model": src,
                    "target_model": tgt,
                    "relationship_type": rel["relationship_type"],
                    "foreign_key_field": rel.get("foreign_key_field"),
                    "back_populates": rel.get("back_populates"),
                    "secondary_table": rel.get("secondary_table"),
                    "description": rel.get("description", "relates_to"),
                    "metadata": rel.get("metadata", {}),
                })

        # 2. Process Foreign Keys declared in model fields
        for model in models:
            for field in model["fields"]:
                if field.get("is_foreign_key") and field.get("foreign_key_target"):
                    fk_target = field["foreign_key_target"]
                    target_tbl = fk_target.split(".")[0]

                    target_model = None
                    if target_tbl in models_by_table:
                        target_model = models_by_table[target_tbl]["name"]
                    elif target_tbl in models_by_name:
                        target_model = models_by_name[target_tbl]["name"]
                    else:
                        target_model = self._table_to_class_name(target_tbl)

                    src = target_model  # Parent (e.g. User)
                    tgt = model["name"] # Child (e.g. Order)

                    key = (src, tgt, "ONE_TO_MANY", field["name"])
                    key_fk = (src, tgt, "FOREIGN_KEY", field["name"])

                    if key not in seen_rels and key_fk not in seen_rels:
                        seen_rels.add(key)
                        relationships.append({
                            "source_model": src,
                            "target_model": tgt,
                            "relationship_type": "ONE_TO_MANY",
                            "foreign_key_field": field["name"],
                            "back_populates": None,
                            "secondary_table": None,
                            "description": "places" if "order" in tgt.lower() else "has",
                            "metadata": {"inferred_from_fk": True},
                        })

        return relationships

    def generate_mermaid_er(
        self, models: List[Dict[str, Any]], relationships: List[Dict[str, Any]]
    ) -> str:
        """
        Generates Mermaid ER diagram syntax:
        Example:
        erDiagram
            USER ||--o{ ORDER : places
            USER {
                int id PK
                string email
            }
        """
        if not models:
            return "erDiagram\n    %% No database models detected in repository\n"

        lines = ["erDiagram"]

        # 1. Render Relationships
        for rel in relationships:
            src = self._sanitize_mermaid_ident(rel["source_model"])
            tgt = self._sanitize_mermaid_ident(rel["target_model"])
            rel_type = rel.get("relationship_type", "ONE_TO_MANY").upper()
            label = rel.get("description") or rel.get("back_populates") or "relates"
            label_clean = re.sub(r'[^a-zA-Z0-9_]', '_', label).strip('_') or "relates"

            # Mermaid cardinality connectors
            if rel_type == "ONE_TO_ONE":
                connector = "||--||"
            elif rel_type in ("ONE_TO_MANY", "FOREIGN_KEY"):
                connector = "||--o{"
            elif rel_type == "MANY_TO_MANY":
                connector = "}o--o{"
            else:
                connector = "||--o{"

            lines.append(f"    {src} {connector} {tgt} : {label_clean}")

        lines.append("")

        # 2. Render Entity Schemas with Fields
        for model in models:
            m_name = self._sanitize_mermaid_ident(model["name"])
            lines.append(f"    {m_name} {{")

            fields = model.get("fields", [])
            for f in fields:
                fname = re.sub(r'[^a-zA-Z0-9_]', '_', f["name"])
                dtype = self._clean_mermaid_type(f.get("data_type", "string"))

                flags = []
                if f.get("is_primary_key"):
                    flags.append("PK")
                if f.get("is_foreign_key"):
                    flags.append("FK")

                flag_str = f" {' '.join(flags)}" if flags else ""
                lines.append(f"        {dtype} {fname}{flag_str}")

            lines.append("    }")

        return "\n".join(lines)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _format_node(self, node: Optional[ast.AST]) -> str:
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Attribute):
            return f"{self._format_node(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            func_name = self._format_node(node.func)
            args_str = ", ".join(self._format_node(a) for a in node.args)
            return f"{func_name}({args_str})"
        elif isinstance(node, ast.Subscript):
            val = self._format_node(node.value)
            sl = self._format_node(node.slice)
            return f"{val}[{sl}]"
        return ""

    def _extract_fk_target(self, arg_node: ast.AST) -> Optional[str]:
        """Extracts 'users.id' from ForeignKey('users.id')"""
        if isinstance(arg_node, ast.Call) and arg_node.args:
            first_arg = arg_node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                return first_arg.value
        return None

    def _is_truthy(self, node: Optional[ast.AST]) -> bool:
        if isinstance(node, ast.Constant):
            return bool(node.value)
        return False

    def _clean_data_type(self, raw_type: str) -> str:
        t = raw_type.split(".")[-1]
        t = t.replace("()", "")
        return t or "String"

    def _python_type_to_sql(self, py_type: str) -> str:
        pt = py_type.lower()
        if "int" in pt:
            return "Integer"
        elif "str" in pt:
            return "String"
        elif "bool" in pt:
            return "Boolean"
        elif "float" in pt:
            return "Float"
        elif "datetime" in pt:
            return "DateTime"
        elif "uuid" in pt:
            return "UUID"
        return "String"

    def _clean_mermaid_type(self, data_type: str) -> str:
        dt = data_type.lower()
        if "int" in dt:
            return "int"
        elif "str" in dt or "char" in dt or "text" in dt:
            return "string"
        elif "bool" in dt:
            return "boolean"
        elif "time" in dt or "date" in dt:
            return "datetime"
        elif "float" in dt or "decimal" in dt or "numeric" in dt:
            return "float"
        return "string"

    def _sanitize_mermaid_ident(self, name: str) -> str:
        clean = re.sub(r'[^a-zA-Z0-9_]', '', name)
        return clean.upper() or "ENTITY"

    def _pluralize(self, word: str) -> str:
        if word.endswith("y") and not word.endswith(("ay", "ey", "oy", "uy")):
            return word[:-1] + "ies"
        elif word.endswith(("s", "sh", "ch", "x", "z")):
            return word + "es"
        return word + "s"

    def _table_to_class_name(self, table_name: str) -> str:
        words = table_name.split("_")
        singular_words = []
        for idx, w in enumerate(words):
            if idx == len(words) - 1:
                # Singularize last word
                if w.endswith("ies"):
                    w = w[:-3] + "y"
                elif w.endswith("es") and len(w) > 3:
                    w = w[:-2]
                elif w.endswith("s") and not w.endswith("ss") and len(w) > 2:
                    w = w[:-1]
            singular_words.append(w.capitalize())
        return "".join(singular_words) or "Model"

    def _split_sql_column_lines(self, body_text: str) -> List[str]:
        items = []
        current = []
        depth = 0
        for char in body_text:
            if char == "(":
                depth += 1
                current.append(char)
            elif char == ")":
                depth -= 1
                current.append(char)
            elif char == "," and depth == 0:
                items.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        if current:
            items.append("".join(current).strip())
        return items


database_structure_analyzer = StaticDatabaseStructureAnalyzer()
