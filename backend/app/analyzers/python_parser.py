import ast
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.core.logging import logger
from backend.app.schemas.entity import CodeEntityBase, EntityType


class PythonParser:
    @staticmethod
    def _safe_unparse(node: Optional[ast.AST]) -> Optional[str]:
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except Exception:
            return None

    @classmethod
    def _extract_decorators(cls, decorator_list: List[ast.expr]) -> List[str]:
        decorators = []
        for dec in decorator_list:
            unparsed = cls._safe_unparse(dec)
            if unparsed:
                decorators.append(unparsed)
        return decorators

    @classmethod
    def _extract_parameters(cls, args: ast.arguments) -> List[Dict[str, Any]]:
        params: List[Dict[str, Any]] = []

        # Position-only args
        for arg in args.posonlyargs:
            params.append({
                "name": arg.arg,
                "type": cls._safe_unparse(arg.annotation),
                "default": None,
                "kind": "posonly",
            })

        # Regular args
        num_defaults = len(args.defaults)
        num_args = len(args.args)
        default_offset = num_args - num_defaults

        for i, arg in enumerate(args.args):
            default_val = None
            if i >= default_offset:
                default_val = cls._safe_unparse(args.defaults[i - default_offset])

            params.append({
                "name": arg.arg,
                "type": cls._safe_unparse(arg.annotation),
                "default": default_val,
                "kind": "standard",
            })

        # *args
        if args.vararg:
            params.append({
                "name": f"*{args.vararg.arg}",
                "type": cls._safe_unparse(args.vararg.annotation),
                "default": None,
                "kind": "vararg",
            })

        # Keyword-only args
        for i, arg in enumerate(args.kwonlyargs):
            default_val = None
            if i < len(args.kw_defaults) and args.kw_defaults[i] is not None:
                default_val = cls._safe_unparse(args.kw_defaults[i])

            params.append({
                "name": arg.arg,
                "type": cls._safe_unparse(arg.annotation),
                "default": default_val,
                "kind": "kwonly",
            })

        # **kwargs
        if args.kwarg:
            params.append({
                "name": f"**{args.kwarg.arg}",
                "type": cls._safe_unparse(args.kwarg.annotation),
                "default": None,
                "kind": "kwarg",
            })

        return params

    @classmethod
    def _build_function_signature(
        cls,
        name: str,
        params: List[Dict[str, Any]],
        return_type: Optional[str],
        is_async: bool,
    ) -> str:
        param_strs = []
        for p in params:
            s = p["name"]
            if p["type"]:
                s += f": {p['type']}"
            if p["default"]:
                s += f" = {p['default']}"
            param_strs.append(s)

        prefix = "async def " if is_async else "def "
        sig = f"{prefix}{name}({', '.join(param_strs)})"
        if return_type:
            sig += f" -> {return_type}"
        return sig

    @classmethod
    def parse_source(cls, source_code: str, file_path: str) -> List[CodeEntityBase]:
        entities: List[CodeEntityBase] = []
        lines = source_code.splitlines()
        total_lines = max(len(lines), 1)

        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError as e:
            logger.warning(f"Syntax error parsing Python file {file_path}: {e}")
            # Still return a MODULE entity
            entities.append(
                CodeEntityBase(
                    name=Path(file_path).stem,
                    entity_type=EntityType.MODULE.value,
                    file_path=file_path,
                    start_line=1,
                    end_line=total_lines,
                    signature=f"module {Path(file_path).name}",
                    docstring=None,
                    metadata_json={"error": f"SyntaxError: {str(e)}"},
                )
            )
            return entities

        # 1. Module Level Entity
        module_docstring = ast.get_docstring(tree)
        imports: List[Dict[str, Any]] = []

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "name": alias.name,
                        "alias": alias.asname,
                    })
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append({
                        "module": mod,
                        "name": alias.name,
                        "alias": alias.asname,
                    })

        module_entity = CodeEntityBase(
            name=Path(file_path).stem,
            entity_type=EntityType.MODULE.value,
            file_path=file_path,
            start_line=1,
            end_line=total_lines,
            signature=f"module {Path(file_path).name}",
            docstring=module_docstring,
            metadata_json={
                "imports": imports,
                "total_lines": total_lines,
            },
        )
        entities.append(module_entity)

        # 2. Extract Classes, Methods, and Functions
        def visit_class(class_node: ast.ClassDef):
            bases = [cls._safe_unparse(b) for b in class_node.bases if cls._safe_unparse(b)]
            decorators = cls._extract_decorators(class_node.decorator_list)
            class_doc = ast.get_docstring(class_node)
            start_l = class_node.lineno
            end_l = getattr(class_node, "end_lineno", start_l)

            base_str = f"({', '.join(bases)})" if bases else ""
            class_sig = f"class {class_node.name}{base_str}:"

            method_names: List[str] = []

            for item in class_node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_names.append(item.name)
                    visit_function(item, parent_class=class_node.name)
                elif isinstance(item, ast.ClassDef):
                    # Nested class
                    visit_class(item)

            entities.append(
                CodeEntityBase(
                    name=class_node.name,
                    entity_type=EntityType.CLASS.value,
                    file_path=file_path,
                    start_line=start_l,
                    end_line=end_l,
                    signature=class_sig,
                    parent_entity=None,
                    docstring=class_doc,
                    metadata_json={
                        "bases": bases,
                        "decorators": decorators,
                        "methods": method_names,
                    },
                )
            )

        def visit_function(func_node: ast.FunctionDef | ast.AsyncFunctionDef, parent_class: Optional[str] = None):
            is_async = isinstance(func_node, ast.AsyncFunctionDef)
            decorators = cls._extract_decorators(func_node.decorator_list)
            params = cls._extract_parameters(func_node.args)
            return_type = cls._safe_unparse(func_node.returns)
            func_doc = ast.get_docstring(func_node)
            start_l = func_node.lineno
            end_l = getattr(func_node, "end_lineno", start_l)

            is_classmethod = any(d in ["classmethod", "@classmethod"] for d in decorators)
            is_staticmethod = any(d in ["staticmethod", "@staticmethod"] for d in decorators)

            signature = cls._build_function_signature(
                name=func_node.name,
                params=params,
                return_type=return_type,
                is_async=is_async,
            )

            entity_type = EntityType.METHOD.value if parent_class else EntityType.FUNCTION.value

            entities.append(
                CodeEntityBase(
                    name=func_node.name,
                    entity_type=entity_type,
                    file_path=file_path,
                    start_line=start_l,
                    end_line=end_l,
                    signature=signature,
                    parent_entity=parent_class,
                    docstring=func_doc,
                    metadata_json={
                        "is_async": is_async,
                        "parameters": params,
                        "return_type": return_type,
                        "decorators": decorators,
                        "is_classmethod": is_classmethod,
                        "is_staticmethod": is_staticmethod,
                    },
                )
            )

        # Traverse top-level body items
        for item in tree.body:
            if isinstance(item, ast.ClassDef):
                visit_class(item)
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit_function(item)

        return entities
