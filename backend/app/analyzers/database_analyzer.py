import ast
import re
from pathlib import Path
from typing import List, Dict, Optional, Any, Set, Tuple
from backend.app.core.logging import logger
from backend.app.schemas.database_schema import (
    DatabaseModelBase,
    DatabaseField,
    DatabaseRelationship,
)
from backend.app.analyzers.code_parser import PYTHON_EXTENSIONS


TYPE_MAP = {
    "int": "INTEGER",
    "integer": "INTEGER",
    "smallint": "SMALLINT",
    "bigint": "BIGINT",
    "str": "VARCHAR",
    "string": "VARCHAR",
    "text": "TEXT",
    "bool": "BOOLEAN",
    "boolean": "BOOLEAN",
    "float": "FLOAT",
    "datetime": "TIMESTAMP",
    "date": "DATE",
    "time": "TIME",
    "json": "JSON",
    "dict": "JSON",
    "uuid": "UUID",
    "numeric": "NUMERIC",
    "decimal": "DECIMAL",
}


class DatabaseAnalyzer:
    @staticmethod
    def _read_file(file_path: Path) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None

    @classmethod
    def analyze_repository(cls, repo_dir: Path) -> Dict[str, Any]:
        models: List[DatabaseModelBase] = []
        relationships: List[DatabaseRelationship] = []

        model_name_to_table: Dict[str, str] = {}
        table_to_model: Dict[str, str] = {}

        # 1. Scan Python files for SQLAlchemy and Django ORM models
        for path in repo_dir.rglob("*.py"):
            rel_path = str(path.relative_to(repo_dir)).replace("\\", "/")
            parts = Path(rel_path).parts
            if any(p.startswith(".") or p in ["node_modules", "dist", "build", "venv", ".venv", "__pycache__"] for p in parts):
                continue

            content = cls._read_file(path)
            if not content:
                continue

            py_models = cls._parse_python_db_models(content, rel_path)
            models.extend(py_models)

        # 2. Scan .sql files for raw SQL CREATE TABLE definitions
        for path in repo_dir.rglob("*.sql"):
            rel_path = str(path.relative_to(repo_dir)).replace("\\", "/")
            parts = Path(rel_path).parts
            if any(p.startswith(".") or p in ["node_modules", "dist", "build", "venv", ".venv"] for p in parts):
                continue

            content = cls._read_file(path)
            if not content:
                continue

            sql_models = cls._parse_raw_sql_models(content, rel_path)
            models.extend(sql_models)

        # Index model names to tables
        for m in models:
            model_name_to_table[m.model_name] = m.table_name
            table_to_model[m.table_name] = m.model_name

        # 3. Resolve relationships across all models
        seen_rel_keys: Set[str] = set()

        for m in models:
            for rel in m.relationships:
                # Resolve target table if missing
                if not rel.target_table or rel.target_table == rel.target_model:
                    if rel.target_model in model_name_to_table:
                        rel.target_table = model_name_to_table[rel.target_model]
                    else:
                        rel.target_table = rel.target_model.lower() + "s"

                key = f"{rel.source_table}->{rel.target_table}:{rel.relationship_type}:{rel.foreign_key}"
                if key not in seen_rel_keys:
                    seen_rel_keys.add(key)
                    relationships.append(rel)

            # Also check Foreign Key columns directly to create FOREIGN_KEY relationships if not explicit
            for f in m.fields:
                if f.foreign_key:
                    target_tbl = f.foreign_key.split(".")[0]
                    tgt_model = table_to_model.get(target_tbl, target_tbl.capitalize())

                    # Check if already covered by ORM relationship
                    has_orm_rel = any(
                        r.source_table == m.table_name and (r.target_table == target_tbl or r.foreign_key == f.name)
                        for r in m.relationships
                    )
                    if not has_orm_rel:
                        fk_rel = DatabaseRelationship(
                            name=f"{m.table_name}_{f.name}_fk",
                            source_model=m.model_name,
                            source_table=m.table_name,
                            target_model=tgt_model,
                            target_table=target_tbl,
                            relationship_type="FOREIGN_KEY",
                            foreign_key=f.name,
                            confidence=1.0,
                            cardinality_mermaid="}|--||",
                            description=f"{m.table_name}.{f.name} references {f.foreign_key}",
                        )
                        key = f"{m.table_name}->{target_tbl}:FOREIGN_KEY:{f.name}"
                        if key not in seen_rel_keys:
                            seen_rel_keys.add(key)
                            relationships.append(fk_rel)

        # 4. Generate Mermaid ER Diagram Code
        mermaid_code = cls.generate_mermaid_er(models, relationships)

        return {
            "models": models,
            "relationships": relationships,
            "total_models": len(models),
            "total_relationships": len(relationships),
            "mermaid_code": mermaid_code,
        }

    # =========================================================================
    # Python SQLAlchemy & Django ORM Parser
    # =========================================================================

    @classmethod
    def _parse_python_db_models(cls, content: str, file_path: str) -> List[DatabaseModelBase]:
        models: List[DatabaseModelBase] = []
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            return models

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it looks like a DB Model
                is_sqlalchemy = False
                is_django = False
                table_name = None

                # Check bases
                for base in node.bases:
                    base_str = ast.unparse(base).lower()
                    if any(b in base_str for b in ["base", "declarativebase", "model", "db.model", "models.model"]):
                        if "models.model" in base_str or "model" in base_str:
                            is_django = True
                        is_sqlalchemy = True

                # Check __tablename__
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == "__tablename__":
                                is_sqlalchemy = True
                                if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                                    table_name = item.value.value

                if not is_sqlalchemy and not is_django and not table_name:
                    continue

                if not table_name:
                    # Default pluralized model name
                    table_name = node.name.lower() + "s"

                orm_framework = "Django" if (is_django and not is_sqlalchemy) else "SQLAlchemy"
                docstring = ast.get_docstring(node)

                fields: List[DatabaseField] = []
                relationships: List[DatabaseRelationship] = []

                # Extract fields & relationships from class body
                for item in node.body:
                    # 1. Annotated assignments: id: Mapped[int] = mapped_column(...)
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        field_name = item.target.id
                        ann_str = ast.unparse(item.annotation)
                        val_str = ast.unparse(item.value) if item.value else ""

                        # Check if relationship: Mapped[List["Project"]] = relationship(...)
                        if "relationship" in val_str.lower() or "relationship" in ann_str.lower():
                            rel = cls._extract_sqlalchemy_relationship(
                                source_model=node.name,
                                source_table=table_name,
                                field_name=field_name,
                                call_node=item.value,
                                ann_str=ann_str,
                            )
                            if rel:
                                relationships.append(rel)
                        else:
                            field = cls._extract_sqlalchemy_field(
                                field_name=field_name,
                                ann_str=ann_str,
                                val_node=item.value,
                            )
                            if field:
                                fields.append(field)

                    # 2. Regular assignments: id = Column(Integer, primary_key=True) or name = models.CharField(...)
                    elif isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id != "__tablename__":
                                field_name = target.id
                                val_str = ast.unparse(item.value) if item.value else ""

                                if "relationship" in val_str.lower():
                                    rel = cls._extract_sqlalchemy_relationship(
                                        source_model=node.name,
                                        source_table=table_name,
                                        field_name=field_name,
                                        call_node=item.value,
                                        ann_str="",
                                    )
                                    if rel:
                                        relationships.append(rel)
                                elif any(k in val_str for k in ["Column", "mapped_column", "models."]):
                                    field = cls._extract_field_from_call(
                                        field_name=field_name,
                                        val_node=item.value,
                                        orm_framework=orm_framework,
                                        source_model=node.name,
                                        source_table=table_name,
                                    )
                                    if isinstance(field, DatabaseField):
                                        fields.append(field)
                                    elif isinstance(field, DatabaseRelationship):
                                        relationships.append(field)

                if fields or relationships:
                    models.append(
                        DatabaseModelBase(
                            model_name=node.name,
                            table_name=table_name,
                            file_path=file_path,
                            line_number=node.lineno,
                            orm_framework=orm_framework,
                            docstring=docstring,
                            fields=fields,
                            relationships=relationships,
                            metadata_json={
                                "field_count": len(fields),
                                "rel_count": len(relationships),
                            },
                        )
                    )

        return models

    @classmethod
    def _extract_sqlalchemy_field(
        cls, field_name: str, ann_str: str, val_node: Optional[ast.AST]
    ) -> DatabaseField:
        # Determine data type from Mapped[type] or mapped_column(Type)
        data_type = "VARCHAR"
        clean_ann = ann_str.replace("Mapped[", "").replace("Optional[", "").rstrip("]").strip()

        for k, v in TYPE_MAP.items():
            if k in clean_ann.lower():
                data_type = v
                break

        primary_key = False
        foreign_key: Optional[str] = None
        nullable = "Optional" in ann_str
        unique = False
        index = False
        default_val: Optional[str] = None

        if isinstance(val_node, ast.Call):
            call_str = ast.unparse(val_node)
            # Inspect first arg for type if specified
            if val_node.args:
                arg0 = ast.unparse(val_node.args[0])
                for k, v in TYPE_MAP.items():
                    if k in arg0.lower():
                        data_type = v
                        break

            # Inspect keyword args
            for kw in val_node.keywords:
                if kw.arg == "primary_key" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    primary_key = True
                    nullable = False
                elif kw.arg == "nullable" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, bool):
                    nullable = kw.value.value
                elif kw.arg == "unique" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    unique = True
                elif kw.arg == "index" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    index = True
                elif kw.arg == "default":
                    default_val = ast.unparse(kw.value)

            # Inspect ForeignKey in args or keywords
            fk_match = re.search(r"""ForeignKey\(['"]([^'"]+)['"]""", call_str)
            if fk_match:
                foreign_key = fk_match.group(1)

        return DatabaseField(
            name=field_name,
            data_type=data_type,
            primary_key=primary_key,
            foreign_key=foreign_key,
            nullable=nullable,
            default=default_val,
            unique=unique,
            index=index,
        )

    @classmethod
    def _extract_field_from_call(
        cls,
        field_name: str,
        val_node: Optional[ast.AST],
        orm_framework: str,
        source_model: str,
        source_table: str,
    ) -> Optional[DatabaseField | DatabaseRelationship]:
        if not isinstance(val_node, ast.Call):
            return None

        call_str = ast.unparse(val_node)

        # Django ForeignKey / ManyToMany / OneToOne
        if "models.ForeignKey" in call_str:
            target = "Target"
            if val_node.args:
                target = ast.unparse(val_node.args[0]).strip("'\"")
            return DatabaseRelationship(
                name=field_name,
                source_model=source_model,
                source_table=source_table,
                target_model=target,
                target_table=target.lower() + "s",
                relationship_type="ONE_TO_MANY",
                foreign_key=field_name + "_id",
                cardinality_mermaid="||--o{",
            )

        if "models.ManyToManyField" in call_str:
            target = "Target"
            if val_node.args:
                target = ast.unparse(val_node.args[0]).strip("'\"")
            return DatabaseRelationship(
                name=field_name,
                source_model=source_model,
                source_table=source_table,
                target_model=target,
                target_table=target.lower() + "s",
                relationship_type="MANY_TO_MANY",
                cardinality_mermaid="}o--o{",
            )

        if "models.OneToOneField" in call_str:
            target = "Target"
            if val_node.args:
                target = ast.unparse(val_node.args[0]).strip("'\"")
            return DatabaseRelationship(
                name=field_name,
                source_model=source_model,
                source_table=source_table,
                target_model=target,
                target_table=target.lower() + "s",
                relationship_type="ONE_TO_ONE",
                cardinality_mermaid="||--||",
            )

        # Legacy Column(...)
        data_type = "VARCHAR"
        for k, v in TYPE_MAP.items():
            if k in call_str.lower():
                data_type = v
                break

        primary_key = "primary_key=True" in call_str
        nullable = "nullable=False" not in call_str
        unique = "unique=True" in call_str
        index = "index=True" in call_str

        fk_match = re.search(r"""ForeignKey\(['"]([^'"]+)['"]""", call_str)
        foreign_key = fk_match.group(1) if fk_match else None

        return DatabaseField(
            name=field_name,
            data_type=data_type,
            primary_key=primary_key,
            foreign_key=foreign_key,
            nullable=nullable,
            unique=unique,
            index=index,
        )

    @classmethod
    def _extract_sqlalchemy_relationship(
        cls,
        source_model: str,
        source_table: str,
        field_name: str,
        call_node: Optional[ast.AST],
        ann_str: str,
    ) -> Optional[DatabaseRelationship]:
        target_model = "Target"
        back_populates: Optional[str] = None
        secondary: Optional[str] = None
        uselist = "List[" in ann_str

        if isinstance(call_node, ast.Call):
            if call_node.args:
                target_model = ast.unparse(call_node.args[0]).strip("'\"")

            for kw in call_node.keywords:
                if kw.arg == "back_populates" and isinstance(kw.value, ast.Constant):
                    back_populates = str(kw.value.value)
                elif kw.arg == "secondary" and isinstance(kw.value, ast.Constant):
                    secondary = str(kw.value.value)
                elif kw.arg == "uselist" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, bool):
                    uselist = kw.value.value

        if not target_model or target_model == "Target":
            # Extract from type annotation
            m_match = re.search(r"""(?:List\[)?['"]?([A-Za-z0-9_]+)['"]?\]?""", ann_str)
            if m_match:
                target_model = m_match.group(1)

        # Determine type
        if secondary:
            rel_type = "MANY_TO_MANY"
            cardinality = "}o--o{"
        elif not uselist:
            rel_type = "ONE_TO_ONE"
            cardinality = "||--||"
        else:
            rel_type = "ONE_TO_MANY"
            cardinality = "||--o{"

        return DatabaseRelationship(
            name=field_name,
            source_model=source_model,
            source_table=source_table,
            target_model=target_model,
            target_table=target_model.lower() + "s",
            relationship_type=rel_type,
            back_populates=back_populates,
            secondary_table=secondary,
            cardinality_mermaid=cardinality,
            description=f"{source_model} {rel_type.lower().replace('_', ' ')} {target_model}",
        )

    # =========================================================================
    # Raw SQL Schema Parser
    # =========================================================================

    @classmethod
    def _parse_raw_sql_models(cls, content: str, file_path: str) -> List[DatabaseModelBase]:
        models: List[DatabaseModelBase] = []

        table_pattern = re.compile(
            r"""CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"']?\w+[`"']?)\s*\((.*?)\);""",
            re.IGNORECASE | re.DOTALL,
        )

        for match in table_pattern.finditer(content):
            raw_table_name = match.group(1).strip("`\"'")
            table_body = match.group(2)

            model_name = "".join(p.capitalize() for p in raw_table_name.rstrip("s").split("_"))
            fields: List[DatabaseField] = []
            relationships: List[DatabaseRelationship] = []

            # Split statements by comma
            lines = [l.strip() for l in table_body.split(",") if l.strip()]

            for line in lines:
                line_lower = line.lower()
                # Check for table-level FOREIGN KEY (col) REFERENCES other_table(id)
                fk_table_match = re.search(
                    r"""FOREIGN\s+KEY\s*\(([`"']?\w+[`"']?)\)\s+REFERENCES\s+([`"']?\w+[`"']?)\s*\(([`"']?\w+[`"']?)\)""",
                    line,
                    re.IGNORECASE,
                )
                if fk_table_match:
                    src_col = fk_table_match.group(1).strip("`\"'")
                    tgt_tbl = fk_table_match.group(2).strip("`\"'")
                    tgt_col = fk_table_match.group(3).strip("`\"'")

                    relationships.append(
                        DatabaseRelationship(
                            name=f"{raw_table_name}_{src_col}_fk",
                            source_model=model_name,
                            source_table=raw_table_name,
                            target_model="".join(p.capitalize() for p in tgt_tbl.rstrip("s").split("_")),
                            target_table=tgt_tbl,
                            relationship_type="FOREIGN_KEY",
                            foreign_key=f"{tgt_tbl}.{tgt_col}",
                            cardinality_mermaid="}|--||",
                        )
                    )
                    continue

                # Check for table-level PRIMARY KEY (id)
                if line_lower.startswith("primary key") or line_lower.startswith("constraint"):
                    continue

                # Column line: col_name TYPE constraints
                tokens = line.split()
                if len(tokens) >= 2:
                    col_name = tokens[0].strip("`\"'")
                    raw_type = tokens[1].upper()

                    data_type = "VARCHAR"
                    for k, v in TYPE_MAP.items():
                        if k in raw_type.lower():
                            data_type = v
                            break

                    is_pk = "primary key" in line_lower
                    is_nullable = "not null" not in line_lower
                    is_unique = "unique" in line_lower

                    fk_inline = re.search(r"""references\s+([`"']?\w+[`"']?)\s*\(([`"']?\w+[`"']?)\)""", line, re.IGNORECASE)
                    fk_target = None
                    if fk_inline:
                        tgt_tbl = fk_inline.group(1).strip("`\"'")
                        tgt_col = fk_inline.group(2).strip("`\"'")
                        fk_target = f"{tgt_tbl}.{tgt_col}"

                    fields.append(
                        DatabaseField(
                            name=col_name,
                            data_type=data_type,
                            primary_key=is_pk,
                            foreign_key=fk_target,
                            nullable=is_nullable,
                            unique=is_unique,
                        )
                    )

            if fields:
                models.append(
                    DatabaseModelBase(
                        model_name=model_name,
                        table_name=raw_table_name,
                        file_path=file_path,
                        orm_framework="RawSQL",
                        fields=fields,
                        relationships=relationships,
                    )
                )

        return models

    # =========================================================================
    # Mermaid ER Diagram Generator
    # =========================================================================

    @classmethod
    def generate_mermaid_er(
        cls, models: List[DatabaseModelBase], relationships: List[DatabaseRelationship]
    ) -> str:
        lines: List[str] = ["erDiagram"]

        # 1. Output entities and their fields
        for m in models:
            lines.append(f"    {m.table_name} {{")
            for f in m.fields:
                pk_fk = ""
                if f.primary_key:
                    pk_fk = " PK"
                elif f.foreign_key:
                    pk_fk = " FK"

                type_clean = f.data_type.lower()
                lines.append(f"        {type_clean} {f.name}{pk_fk}")
            lines.append("    }")

        # 2. Output relationships
        for rel in relationships:
            src = rel.source_table
            tgt = rel.target_table
            card = rel.cardinality_mermaid or "||--o{"
            rel_label = rel.relationship_type.lower().replace("_", " ")

            lines.append(f'    {src} {card} {tgt} : "{rel_label}"')

        return "\n".join(lines)
