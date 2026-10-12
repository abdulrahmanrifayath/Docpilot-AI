import ast
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.parsers.base import (
    APIEndpoint,
    BaseParser,
    CodeSymbol,
    DatabaseModel,
    DBField,
    DBRelationship,
    ImportItem,
    ParameterItem,
    ParsedFile,
)


class CallVisitor(ast.NodeVisitor):
    """Collects function and method call names within an AST subtree."""

    def __init__(self) -> None:
        self.calls: Set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.add(node.func.attr)
        self.generic_visit(node)


class PythonParser(BaseParser):
    def parse(self, file_path: str, relative_path: str, content: str) -> ParsedFile:
        lines = content.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))

        parsed = ParsedFile(
            file_path=file_path,
            relative_path=relative_path,
            language="Python",
            lines_of_code=total_lines - blank_lines - comment_lines,
            blank_lines=blank_lines,
            comment_lines=comment_lines,
        )

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            # Fallback regex parsing if syntax error (e.g. template or incompatible syntax)
            parsed.raw_summary = "Syntax error encountered during AST parsing."
            return self._regex_fallback(parsed, lines)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._parse_import(node, parsed)
            elif isinstance(node, ast.ClassDef):
                self._parse_class(node, parsed)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._parse_function(node, parsed)

        return parsed

    def _parse_import(self, node: ast.AST, parsed: ParsedFile) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                parsed.imports.append(
                    ImportItem(
                        module=alias.name,
                        alias=alias.asname,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            names = [alias.name for alias in node.names]
            parsed.imports.append(
                ImportItem(
                    module=module_name,
                    imported_names=names,
                    is_relative=bool(node.level and node.level > 0),
                )
            )

    def _parse_class(self, node: ast.ClassDef, parsed: ParsedFile) -> None:
        base_names = [self._format_node(base) for base in node.bases]
        docstring = ast.get_docstring(node)
        decorator_names = [self._format_node(dec) for dec in node.decorator_list]

        # Check if class is an ORM database model
        is_orm = any(
            b in {"Base", "db.Model", "Model", "DeclarativeBase", "Document"} or "Base" in b or "Model" in b
            for b in base_names
        )

        class_symbol = CodeSymbol(
            name=node.name,
            symbol_type="class",
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            docstring=docstring,
            decorators=decorator_names,
        )
        parsed.classes.append(class_symbol)

        # Parse methods & class body
        db_fields: List[DBField] = []
        db_relationships: List[DBRelationship] = []
        table_name: Optional[str] = None

        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_symbol = self._create_function_symbol(child, parent_class=node.name)
                parsed.functions.append(method_symbol)

            elif isinstance(child, ast.Assign) and is_orm:
                # Check for __tablename__ = "users"
                for target in child.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        if isinstance(child.value, ast.Constant) and isinstance(child.value.value, str):
                            table_name = child.value.value

                # Check for Column definitions or Django Field definitions
                field = self._extract_db_field_from_assign(child)
                if field:
                    db_fields.append(field)

                rel = self._extract_db_relationship_from_assign(child)
                if rel:
                    db_relationships.append(rel)

            elif isinstance(child, ast.AnnAssign) and is_orm:
                # Type-annotated SQLModel or SQLAlchemy 2.0 mapped_column
                field = self._extract_db_field_from_annassign(child)
                if field:
                    db_fields.append(field)

        if is_orm and (db_fields or table_name):
            parsed.db_models.append(
                DatabaseModel(
                    name=node.name,
                    table_name=table_name or node.name.lower() + "s",
                    fields=db_fields,
                    relationships=db_relationships,
                    orm_type="SQLAlchemy" if "Base" in str(base_names) else "ORM",
                    start_line=node.lineno,
                )
            )

    def _parse_function(self, node: ast.AST, parsed: ParsedFile) -> None:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return
        func_symbol = self._create_function_symbol(node)
        parsed.functions.append(func_symbol)

        # Check if function is an API route (FastAPI, Flask, etc.)
        api_endpoint = self._extract_api_endpoint(node)
        if api_endpoint:
            parsed.apis.append(api_endpoint)

    def _create_function_symbol(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent_class: Optional[str] = None,
    ) -> CodeSymbol:
        docstring = ast.get_docstring(node)
        decorators = [self._format_node(d) for d in node.decorator_list]
        return_type = self._format_node(node.returns) if node.returns else None

        parameters: List[ParameterItem] = []
        for arg in node.args.args:
            type_hint = self._format_node(arg.annotation) if arg.annotation else None
            parameters.append(ParameterItem(name=arg.arg, type_hint=type_hint))

        call_visitor = CallVisitor()
        call_visitor.visit(node)

        return CodeSymbol(
            name=node.name,
            symbol_type="async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            decorators=decorators,
            calls=sorted(list(call_visitor.calls)),
            parent_symbol=parent_class,
        )

    def _extract_api_endpoint(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> Optional[APIEndpoint]:
        # Look for decorators like @app.get("/items"), @router.post("/login"), @bp.route("/path")
        http_methods = {"get", "post", "put", "delete", "patch", "options", "head"}
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call):
                func = dec.func
                method_name = None
                if isinstance(func, ast.Attribute) and func.attr.lower() in http_methods:
                    method_name = func.attr.upper()
                elif isinstance(func, ast.Attribute) and func.attr == "route":
                    method_name = "GET"  # default Flask
                    for kw in dec.keywords:
                        if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                            for elt in kw.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    method_name = elt.value.upper()
                                    break

                if method_name:
                    path = "/"
                    if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                        path = dec.args[0].value

                    # Check response model kwarg
                    response_model = None
                    for kw in dec.keywords:
                        if kw.arg in ("response_model", "response"):
                            response_model = self._format_node(kw.value)

                    # Check auth from decorators or parameters
                    auth_required = any(
                        "auth" in d.lower() or "login" in d.lower() or "token" in d.lower() or "jwt" in d.lower()
                        for d in [self._format_node(d) for d in node.decorator_list]
                    )

                    params: List[Dict[str, Any]] = []
                    for arg in node.args.args:
                        if arg.arg not in ("self", "cls"):
                            th = self._format_node(arg.annotation) if arg.annotation else None
                            params.append({"name": arg.arg, "type": th or "any"})
                            if th and ("user" in th.lower() or "token" in th.lower()):
                                auth_required = True

                    return APIEndpoint(
                        method=method_name,
                        path=path,
                        handler_name=node.name,
                        start_line=node.lineno,
                        docstring=ast.get_docstring(node),
                        parameters=params,
                        response_model=response_model,
                        auth_required=auth_required,
                        framework="FastAPI" if "router" in str(self._format_node(dec.func)) or "app" in str(self._format_node(dec.func)) else "REST",
                    )
        return None

    def _extract_db_field_from_assign(self, child: ast.Assign) -> Optional[DBField]:
        if not child.targets or not isinstance(child.targets[0], ast.Name):
            return None
        field_name = child.targets[0].id
        if field_name.startswith("__"):
            return None

        val = child.value
        if isinstance(val, ast.Call):
            call_func = self._format_node(val.func)
            if "Column" in call_func:
                data_type = "String"
                is_pk = False
                is_fk = False
                fk_target = None
                is_nullable = True

                for arg in val.args:
                    arg_str = self._format_node(arg)
                    if "ForeignKey" in arg_str:
                        is_fk = True
                        if isinstance(arg, ast.Call) and arg.args:
                            fk_target = self._format_node(arg.args[0]).strip("'\"")
                    elif any(t in arg_str for t in ["Integer", "String", "Text", "Boolean", "DateTime", "Float", "JSON"]):
                        data_type = arg_str

                for kw in val.keywords:
                    if kw.arg == "primary_key" and isinstance(kw.value, ast.Constant):
                        is_pk = bool(kw.value.value)
                    elif kw.arg == "nullable" and isinstance(kw.value, ast.Constant):
                        is_nullable = bool(kw.value.value)

                return DBField(
                    name=field_name,
                    data_type=data_type,
                    is_primary_key=is_pk,
                    is_foreign_key=is_fk,
                    foreign_key_target=fk_target,
                    is_nullable=is_nullable,
                )
            elif "Field" in call_func or "CharField" in call_func or "IntegerField" in call_func:
                return DBField(
                    name=field_name,
                    data_type=call_func,
                    is_primary_key=field_name.lower() == "id",
                )
        return None

    def _extract_db_field_from_annassign(self, child: ast.AnnAssign) -> Optional[DBField]:
        if not isinstance(child.target, ast.Name):
            return None
        field_name = child.target.id
        type_str = self._format_node(child.annotation)
        is_pk = "primary_key=True" in (self._format_node(child.value) if child.value else "") or field_name.lower() == "id"
        return DBField(
            name=field_name,
            data_type=type_str,
            is_primary_key=is_pk,
        )

    def _extract_db_relationship_from_assign(self, child: ast.Assign) -> Optional[DBRelationship]:
        if not child.targets or not isinstance(child.targets[0], ast.Name):
            return None
        rel_name = child.targets[0].id
        if isinstance(child.value, ast.Call):
            call_func = self._format_node(child.value.func)
            if "relationship" in call_func and child.value.args:
                target = self._format_node(child.value.args[0]).strip("'\"")
                return DBRelationship(
                    name=rel_name,
                    target_model=target,
                    relationship_type="many_to_one" if not rel_name.endswith("s") else "one_to_many",
                )
        return None

    def _format_node(self, node: Optional[ast.AST]) -> str:
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._format_node(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Subscript):
            return f"{self._format_node(node.value)}[{self._format_node(node.slice)}]"
        elif isinstance(node, ast.Call):
            args = [self._format_node(a) for a in node.args]
            return f"{self._format_node(node.func)}({', '.join(args)})"
        try:
            return ast.unparse(node)
        except Exception:
            return str(type(node).__name__)

    def _regex_fallback(self, parsed: ParsedFile, lines: List[str]) -> ParsedFile:
        for idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            # Find class
            class_match = re.match(r"^class\s+([A-Za-z0-9_]+)", line_str)
            if class_match:
                parsed.classes.append(
                    CodeSymbol(
                        name=class_match.group(1),
                        symbol_type="class",
                        start_line=idx,
                        end_line=idx,
                    )
                )
            # Find function
            fn_match = re.match(r"^(?:async\s+)?def\s+([A-Za-z0-9_]+)\s*\(", line_str)
            if fn_match:
                parsed.functions.append(
                    CodeSymbol(
                        name=fn_match.group(1),
                        symbol_type="async_function" if "async" in line_str else "function",
                        start_line=idx,
                        end_line=idx,
                    )
                )
        return parsed
