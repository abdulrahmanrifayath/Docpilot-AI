import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.logging import logger

try:
    from tree_sitter import Language, Parser
    from tree_sitter_languages import get_parser, get_language
    HAS_TREE_SITTER = True
except Exception:
    HAS_TREE_SITTER = False


class ExtractedEntity:
    """Normalized intermediate entity representation before DB persistence."""

    def __init__(
        self,
        name: str,
        entity_type: str,  # MODULE, CLASS, FUNCTION, METHOD, INTERFACE, COMPONENT
        start_line: int,
        end_line: int,
        signature: Optional[str] = None,
        parent_entity: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.entity_type = entity_type
        self.start_line = start_line
        self.end_line = end_line
        self.signature = signature
        self.parent_entity = parent_entity
        self.metadata = metadata or {}

    def to_dict(self, project_id: str, file_path: str) -> Dict[str, Any]:
        return {
            "project_id": project_id,
            "file_path": file_path,
            "name": self.name,
            "entity_type": self.entity_type,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "signature": self.signature,
            "parent_entity": self.parent_entity,
            "metadata_json": self.metadata,
        }


class PythonCodeExtractor:
    """Extracts normalized code entities from Python source code using Python AST."""

    def extract(self, file_path: str, content: str) -> List[ExtractedEntity]:
        entities: List[ExtractedEntity] = []
        lines = content.splitlines()
        total_lines = max(1, len(lines))
        module_name = Path(file_path).stem

        # Try AST parse
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            logger.warning(f"Python AST syntax error in {file_path}: {e}")
            # Minimal module entity
            entities.append(
                ExtractedEntity(
                    name=module_name,
                    entity_type="MODULE",
                    start_line=1,
                    end_line=total_lines,
                    signature=f"module {module_name}",
                    metadata={"syntax_error": str(e)},
                )
            )
            return entities

        # 1. Module Entity
        docstring = ast.get_docstring(tree)
        imports = self._extract_imports(tree)
        entities.append(
            ExtractedEntity(
                name=module_name,
                entity_type="MODULE",
                start_line=1,
                end_line=total_lines,
                signature=f"module {module_name}",
                metadata={"docstring": docstring, "imports": imports},
            )
        )

        # 2. Iterate top-level nodes
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                entities.extend(self._extract_class(node, lines))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                entities.append(self._extract_function(node, lines, parent=None))

        return entities

    def _extract_imports(self, tree: ast.AST) -> List[Dict[str, Any]]:
        imports: List[Dict[str, Any]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "is_relative": False,
                        "imported_names": [alias.name],
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [a.name for a in node.names]
                imports.append({
                    "module": module,
                    "alias": None,
                    "is_relative": bool(node.level and node.level > 0),
                    "imported_names": names,
                })
        return imports

    def _extract_class(self, node: ast.ClassDef, lines: List[str]) -> List[ExtractedEntity]:
        entities: List[ExtractedEntity] = []
        bases = [self._unparse_safe(b) for b in node.bases]
        decorators = [self._unparse_safe(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)

        # Build class signature
        base_str = f"({', '.join(bases)})" if bases else ""
        class_sig = f"class {node.name}{base_str}:"

        entities.append(
            ExtractedEntity(
                name=node.name,
                entity_type="CLASS",
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                signature=class_sig,
                parent_entity=None,
                metadata={
                    "inheritance": bases,
                    "bases": bases,
                    "decorators": decorators,
                    "docstring": docstring,
                },

            )
        )

        # Methods inside class
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_entity = self._extract_function(item, lines, parent=node.name)
                method_entity.entity_type = "METHOD"
                entities.append(method_entity)
            elif isinstance(item, ast.ClassDef):
                # Nested class
                nested = self._extract_class(item, lines)
                if nested:
                    nested[0].parent_entity = node.name
                entities.extend(nested)

        return entities

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        lines: List[str],
        parent: Optional[str] = None,
    ) -> ExtractedEntity:
        is_async = isinstance(node, ast.AsyncFunctionDef)
        decorators = [self._unparse_safe(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)
        params = self._extract_parameters(node.args)

        ret_annotation = self._unparse_safe(node.returns) if node.returns else None

        # Build clean signature
        param_strs = []
        for p in params:
            s = p["name"]
            if p["type_hint"]:
                s += f": {p['type_hint']}"
            if p["default"]:
                s += f" = {p['default']}"
            param_strs.append(s)

        prefix = "async def " if is_async else "def "
        ret_str = f" -> {ret_annotation}" if ret_annotation else ""
        signature = f"{prefix}{node.name}({', '.join(param_strs)}){ret_str}:"

        entity_type = "METHOD" if parent else "FUNCTION"

        return ExtractedEntity(
            name=node.name,
            entity_type=entity_type,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            signature=signature,
            parent_entity=parent,
            metadata={
                "is_async": is_async,
                "decorators": decorators,
                "parameters": params,
                "return_annotation": ret_annotation,
                "return_type": ret_annotation,
                "docstring": docstring,
            },

        )

    def _extract_parameters(self, args: ast.arguments) -> List[Dict[str, Any]]:
        params: List[Dict[str, Any]] = []

        # Position args defaults align from right
        defaults_offset = len(args.args) - len(args.defaults)
        for i, arg in enumerate(args.args):
            type_hint = self._unparse_safe(arg.annotation) if arg.annotation else None
            default_val = None
            if i >= defaults_offset:
                def_idx = i - defaults_offset
                default_val = self._unparse_safe(args.defaults[def_idx])
            params.append({
                "name": arg.arg,
                "type_hint": type_hint,
                "default": default_val,
            })

        # *vararg
        if args.vararg:
            type_hint = self._unparse_safe(args.vararg.annotation) if args.vararg.annotation else None
            params.append({
                "name": f"*{args.vararg.arg}",
                "type_hint": type_hint,
                "default": None,
            })

        # kwonlyargs
        for i, arg in enumerate(args.kwonlyargs):
            type_hint = self._unparse_safe(arg.annotation) if arg.annotation else None
            default_val = None
            if i < len(args.kw_defaults) and args.kw_defaults[i] is not None:
                default_val = self._unparse_safe(args.kw_defaults[i])
            params.append({
                "name": arg.arg,
                "type_hint": type_hint,
                "default": default_val,
            })

        # **kwarg
        if args.kwarg:
            type_hint = self._unparse_safe(args.kwarg.annotation) if args.kwarg.annotation else None
            params.append({
                "name": f"**{args.kwarg.arg}",
                "type_hint": type_hint,
                "default": None,
            })

        return params

    def _unparse_safe(self, node: Optional[ast.AST]) -> str:
        if node is None:
            return ""
        try:
            return ast.unparse(node)
        except Exception:
            return ""


class JsTsCodeExtractor:
    """Extracts normalized code entities from JavaScript and TypeScript source code using Tree-sitter."""

    def __init__(self):
        self._parsers: Dict[str, Any] = {}
        if HAS_TREE_SITTER:
            try:
                self._parsers["typescript"] = get_parser("typescript")
                self._parsers["javascript"] = get_parser("javascript")
                self._parsers["tsx"] = get_parser("tsx")
            except Exception as e:
                logger.warning(f"Failed to load tree-sitter parsers: {e}")

    def extract(self, file_path: str, content: str) -> List[ExtractedEntity]:
        entities: List[ExtractedEntity] = []
        lines = content.splitlines()
        total_lines = max(1, len(lines))
        module_name = Path(file_path).stem
        ext = Path(file_path).suffix.lower()

        is_ts = ext in {".ts", ".tsx", ".mts", ".cts"}
        is_jsx_tsx = ext in {".jsx", ".tsx"}

        parser_key = "tsx" if is_jsx_tsx else ("typescript" if is_ts else "javascript")
        parser = self._parsers.get(parser_key) or self._parsers.get("typescript") or self._parsers.get("javascript")

        if parser and HAS_TREE_SITTER:
            try:
                content_bytes = content.encode("utf-8")
                tree = parser.parse(content_bytes)
                return self._extract_from_tree(tree.root_node, content_bytes, lines, module_name, is_jsx_tsx)
            except Exception as e:
                logger.warning(f"Tree-sitter parse error for {file_path}: {e}")

        # Fallback regex extraction if Tree-sitter failed
        return self._regex_fallback(file_path, content, lines, module_name, is_jsx_tsx)

    def _extract_from_tree(
        self,
        root_node: Any,
        content_bytes: bytes,
        lines: List[str],
        module_name: str,
        is_jsx_tsx: bool,
    ) -> List[ExtractedEntity]:
        entities: List[ExtractedEntity] = []
        imports: List[Dict[str, Any]] = []
        exports: List[str] = []

        def get_text(node: Any) -> str:
            return content_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")

        # 1. Module Entity
        entities.append(
            ExtractedEntity(
                name=module_name,
                entity_type="MODULE",
                start_line=1,
                end_line=len(lines),
                signature=f"module {module_name}",
                metadata={"imports": imports, "exports": exports},
            )
        )

        def visit(node: Any, parent_class: Optional[str] = None):
            ntype = node.type

            # Imports
            if ntype == "import_statement":
                text = get_text(node)
                imports.append({"statement": text})
                return

            # Exports
            if ntype == "export_statement":
                # Inspect inner declaration
                for child in node.children:
                    if child.type in {"function_declaration", "class_declaration", "interface_declaration", "lexical_declaration"}:
                        visit(child, parent_class)
                return

            # Classes
            if ntype == "class_declaration":
                name_node = node.child_by_field_name("name")
                name = get_text(name_node) if name_node else "AnonymousClass"
                start_l = node.start_point[0] + 1
                end_l = node.end_point[0] + 1
                heritage = ""
                for child in node.children:
                    if child.type in {"class_heritage", "extends_clause", "implements_clause"}:
                        heritage += " " + get_text(child)
                sig = f"class {name}{heritage}"

                entities.append(
                    ExtractedEntity(
                        name=name,
                        entity_type="CLASS",
                        start_line=start_l,
                        end_line=end_l,
                        signature=sig.strip(),
                        parent_entity=parent_class,
                        metadata={"heritage": heritage.strip()},
                    )
                )

                # Process methods inside class body
                body_node = node.child_by_field_name("body")
                if body_node:
                    for method_child in body_node.children:
                        if method_child.type in {"method_definition", "public_field_definition"}:
                            visit(method_child, parent_class=name)
                return

            # Methods inside class
            if ntype == "method_definition" and parent_class:
                name_node = node.child_by_field_name("name")
                name = get_text(name_node) if name_node else "method"
                start_l = node.start_point[0] + 1
                end_l = node.end_point[0] + 1
                method_line = lines[start_l - 1].strip() if start_l <= len(lines) else f"{name}()"

                entities.append(
                    ExtractedEntity(
                        name=name,
                        entity_type="METHOD",
                        start_line=start_l,
                        end_line=end_l,
                        signature=method_line,
                        parent_entity=parent_class,
                        metadata={},
                    )
                )
                return

            # Interfaces (TypeScript)
            if ntype in {"interface_declaration", "type_alias_declaration"}:
                name_node = node.child_by_field_name("name")
                name = get_text(name_node) if name_node else "Interface"
                start_l = node.start_point[0] + 1
                end_l = node.end_point[0] + 1
                sig = lines[start_l - 1].strip() if start_l <= len(lines) else f"interface {name}"

                entities.append(
                    ExtractedEntity(
                        name=name,
                        entity_type="INTERFACE",
                        start_line=start_l,
                        end_line=end_l,
                        signature=sig,
                        parent_entity=None,
                        metadata={"declaration_type": ntype},
                    )
                )
                return

            # Function Declarations
            if ntype == "function_declaration":
                name_node = node.child_by_field_name("name")
                name = get_text(name_node) if name_node else "anonymous"
                start_l = node.start_point[0] + 1
                end_l = node.end_point[0] + 1
                sig_line = lines[start_l - 1].strip() if start_l <= len(lines) else f"function {name}()"

                # Check if it's a React Component (Name starts with Uppercase and JSX file or contains JSX)
                is_comp = is_jsx_tsx and name[0].isupper() and self._node_contains_jsx(node)

                entities.append(
                    ExtractedEntity(
                        name=name,
                        entity_type="COMPONENT" if is_comp else "FUNCTION",
                        start_line=start_l,
                        end_line=end_l,
                        signature=sig_line,
                        parent_entity=None,
                        metadata={"is_component": is_comp},
                    )
                )
                return

            # Arrow functions & lexical declarations: const MyComp = () => ...
            if ntype == "lexical_declaration":
                for decl in node.children:
                    if decl.type == "variable_declarator":
                        name_node = decl.child_by_field_name("name")
                        val_node = decl.child_by_field_name("value")
                        if name_node and val_node and val_node.type in {"arrow_function", "function"}:
                            name = get_text(name_node)
                            start_l = decl.start_point[0] + 1
                            end_l = decl.end_point[0] + 1
                            sig_line = lines[start_l - 1].strip() if start_l <= len(lines) else f"const {name} = () =>"

                            is_comp = (
                                is_jsx_tsx
                                and name[0].isupper()
                                and (self._node_contains_jsx(val_node) or "FC" in sig_line or "Component" in sig_line)
                            )

                            entities.append(
                                ExtractedEntity(
                                    name=name,
                                    entity_type="COMPONENT" if is_comp else "FUNCTION",
                                    start_line=start_l,
                                    end_line=end_l,
                                    signature=sig_line,
                                    parent_entity=None,
                                    metadata={"is_arrow_function": True, "is_component": is_comp},
                                )
                            )
                return

            # Recurse children
            for child in node.children:
                visit(child, parent_class)

        visit(root_node)
        return entities

    def _node_contains_jsx(self, node: Any) -> bool:
        """Check if node or its descendants contain JSX markup."""
        if node.type in {"jsx_element", "jsx_self_closing_element", "jsx_fragment"}:
            return True
        for child in node.children:
            if self._node_contains_jsx(child):
                return True
        return False

    def _regex_fallback(
        self,
        file_path: str,
        content: str,
        lines: List[str],
        module_name: str,
        is_jsx_tsx: bool,
    ) -> List[ExtractedEntity]:
        """Regex-based parser for JavaScript and TypeScript."""
        entities: List[ExtractedEntity] = []
        entities.append(
            ExtractedEntity(
                name=module_name,
                entity_type="MODULE",
                start_line=1,
                end_line=len(lines),
                signature=f"module {module_name}",
            )
        )

        class_regex = re.compile(r"class\s+([A-Za-z0-9_$]+)(?:\s+extends\s+([A-Za-z0-9_$.]+))?")
        interface_regex = re.compile(r"(?:interface|type)\s+([A-Za-z0-9_$]+)")
        func_regex = re.compile(r"(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)")
        arrow_regex = re.compile(r"(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*(?::\s*[^=]+)?\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^=]+)?\s*=>")

        for idx, line in enumerate(lines, start=1):
            s = line.strip()

            # Class
            cm = class_regex.search(s)
            if cm:
                cname = cm.group(1)
                entities.append(
                    ExtractedEntity(
                        name=cname,
                        entity_type="CLASS",
                        start_line=idx,
                        end_line=idx,
                        signature=s,
                    )
                )
                continue

            # Interface
            im = interface_regex.search(s)
            if im and ("interface" in s or "type" in s):
                iname = im.group(1)
                entities.append(
                    ExtractedEntity(
                        name=iname,
                        entity_type="INTERFACE",
                        start_line=idx,
                        end_line=idx,
                        signature=s,
                    )
                )
                continue

            # Function
            fm = func_regex.search(s)
            if fm:
                fname = fm.group(1)
                is_comp = is_jsx_tsx and fname[0].isupper()
                entities.append(
                    ExtractedEntity(
                        name=fname,
                        entity_type="COMPONENT" if is_comp else "FUNCTION",
                        start_line=idx,
                        end_line=idx,
                        signature=s,
                    )
                )
                continue

            # Arrow Function / Component
            am = arrow_regex.search(s)
            if am:
                aname = am.group(1)
                is_comp = is_jsx_tsx and aname[0].isupper()
                entities.append(
                    ExtractedEntity(
                        name=aname,
                        entity_type="COMPONENT" if is_comp else "FUNCTION",
                        start_line=idx,
                        end_line=idx,
                        signature=s,
                    )
                )

        return entities


class StaticCodeParsingEngine:
    """Master Static Code Parsing Engine supporting Python, JavaScript, and TypeScript."""

    def __init__(self):
        self.python_extractor = PythonCodeExtractor()
        self.jsts_extractor = JsTsCodeExtractor()

    def parse_file(self, file_path: str, content: str) -> List[ExtractedEntity]:
        ext = Path(file_path).suffix.lower()
        if ext in {".py", ".pyi", ".pyw"}:
            return self.python_extractor.extract(file_path, content)
        elif ext in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}:
            return self.jsts_extractor.extract(file_path, content)
        return []

    def is_supported_file(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in {".py", ".pyi", ".pyw", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}


code_parsing_engine = StaticCodeParsingEngine()
static_code_parser = code_parsing_engine
