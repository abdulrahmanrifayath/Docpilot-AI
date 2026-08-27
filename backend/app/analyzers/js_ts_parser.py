import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import tree_sitter
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts

from backend.app.core.logging import logger
from backend.app.schemas.entity import CodeEntityBase, EntityType


class JsTsParser:
    _js_lang = tree_sitter.Language(tsjs.language())
    _ts_lang = tree_sitter.Language(tsts.language_typescript())
    _tsx_lang = tree_sitter.Language(tsts.language_tsx())

    @classmethod
    def _get_parser_for_file(cls, file_path: str) -> tree_sitter.Parser:
        ext = Path(file_path).suffix.lower()
        if ext in [".tsx", ".jsx"]:
            return tree_sitter.Parser(cls._tsx_lang)
        elif ext in [".ts", ".mts", ".cts"]:
            return tree_sitter.Parser(cls._ts_lang)
        else:
            return tree_sitter.Parser(cls._js_lang)

    @staticmethod
    def _node_text(node: tree_sitter.Node, source_bytes: bytes) -> str:
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    @classmethod
    def _has_jsx_descendant(cls, node: tree_sitter.Node) -> bool:
        jsx_types = {"jsx_element", "jsx_self_closing_element", "jsx_fragment"}
        if node.type in jsx_types:
            return True
        for child in node.children:
            if cls._has_jsx_descendant(child):
                return True
        return False

    @classmethod
    def _clean_signature(cls, full_text: str, max_chars: int = 160) -> str:
        # Extract until the opening brace '{' of the body or arrow '=>'
        lines = full_text.splitlines()
        first_lines = " ".join(lines[:3])
        # Replace multiple whitespace
        clean = re.sub(r"\s+", " ", first_lines).strip()
        if "{" in clean:
            clean = clean.split("{")[0].strip()
        if len(clean) > max_chars:
            clean = clean[:max_chars] + "..."
        return clean

    @classmethod
    def parse_source(cls, source_code: str, file_path: str) -> List[CodeEntityBase]:
        entities: List[CodeEntityBase] = []
        source_bytes = source_code.encode("utf-8")
        total_lines = max(len(source_code.splitlines()), 1)

        try:
            parser = cls._get_parser_for_file(file_path)
            tree = parser.parse(source_bytes)
        except Exception as e:
            logger.warning(f"Error initializing tree-sitter for {file_path}: {e}")
            entities.append(
                CodeEntityBase(
                    name=Path(file_path).stem,
                    entity_type=EntityType.MODULE.value,
                    file_path=file_path,
                    start_line=1,
                    end_line=total_lines,
                    signature=f"module {Path(file_path).name}",
                    docstring=None,
                    metadata_json={"error": f"TreeSitterError: {str(e)}"},
                )
            )
            return entities

        imports: List[Dict[str, Any]] = []
        exports: List[str] = []

        # -------------------------------------------------------------
        # Traversal Helper
        # -------------------------------------------------------------
        def traverse(node: tree_sitter.Node, is_exported_context: bool = False, parent_class: Optional[str] = None):
            nonlocal imports, exports

            # 1. Imports
            if node.type == "import_statement":
                text = cls._node_text(node, source_bytes)
                imports.append({"statement": text.strip()})
                return

            # 2. Exports
            if node.type in ["export_statement", "export_default_declaration"]:
                for child in node.children:
                    if child.type not in ["export", "default"]:
                        traverse(child, is_exported_context=True, parent_class=parent_class)
                return

            # 3. Interfaces (TypeScript)
            if node.type == "interface_declaration":
                name_node = node.child_by_field_name("name")
                name = cls._node_text(name_node, source_bytes) if name_node else "AnonymousInterface"
                start_l = node.start_point[0] + 1
                end_l = node.end_point[0] + 1
                full_text = cls._node_text(node, source_bytes)

                # Extract extends
                extends = []
                for child in node.children:
                    if child.type == "interface_heritage" or child.type == "extends_clause":
                        extends.append(cls._node_text(child, source_bytes).replace("extends", "").strip())

                sig = cls._clean_signature(full_text)
                entities.append(
                    CodeEntityBase(
                        name=name,
                        entity_type=EntityType.INTERFACE.value,
                        file_path=file_path,
                        start_line=start_l,
                        end_line=end_l,
                        signature=sig,
                        parent_entity=None,
                        docstring=None,
                        metadata_json={
                            "extends": extends,
                            "is_exported": is_exported_context,
                        },
                    )
                )
                return

            # 4. Classes
            if node.type in ["class_declaration", "class"]:
                name_node = node.child_by_field_name("name")
                name = cls._node_text(name_node, source_bytes) if name_node else "AnonymousClass"
                start_l = node.start_point[0] + 1
                end_l = node.end_point[0] + 1
                full_text = cls._node_text(node, source_bytes)

                extends = None
                for child in node.children:
                    if child.type in ["class_heritage", "extends_clause"]:
                        extends = cls._node_text(child, source_bytes).replace("extends", "").strip()

                sig = cls._clean_signature(full_text)
                methods: List[str] = []

                # Body items
                body_node = node.child_by_field_name("body")
                if body_node:
                    for child in body_node.children:
                        if child.type == "method_definition":
                            m_name_node = child.child_by_field_name("name")
                            if m_name_node:
                                methods.append(cls._node_text(m_name_node, source_bytes))
                            traverse(child, is_exported_context=False, parent_class=name)

                entities.append(
                    CodeEntityBase(
                        name=name,
                        entity_type=EntityType.CLASS.value,
                        file_path=file_path,
                        start_line=start_l,
                        end_line=end_l,
                        signature=sig,
                        parent_entity=None,
                        docstring=None,
                        metadata_json={
                            "extends": extends,
                            "methods": methods,
                            "is_exported": is_exported_context,
                        },
                    )
                )
                return

            # 5. Methods inside classes
            if node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                name = cls._node_text(name_node, source_bytes) if name_node else "anonymousMethod"
                start_l = node.start_point[0] + 1
                end_l = node.end_point[0] + 1
                full_text = cls._node_text(node, source_bytes)

                is_async = any(c.type == "async" for c in node.children)
                is_static = any(c.type == "static" for c in node.children)
                sig = cls._clean_signature(full_text)

                entities.append(
                    CodeEntityBase(
                        name=name,
                        entity_type=EntityType.METHOD.value,
                        file_path=file_path,
                        start_line=start_l,
                        end_line=end_l,
                        signature=sig,
                        parent_entity=parent_class,
                        docstring=None,
                        metadata_json={
                            "is_async": is_async,
                            "is_static": is_static,
                            "is_constructor": name == "constructor",
                        },
                    )
                )
                return

            # 6. Function Declarations
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                name = cls._node_text(name_node, source_bytes) if name_node else "anonymous"
                start_l = node.start_point[0] + 1
                end_l = node.end_point[0] + 1
                full_text = cls._node_text(node, source_bytes)

                is_async = any(c.type == "async" for c in node.children)
                has_jsx = cls._has_jsx_descendant(node)
                is_component = has_jsx or (name[0].isupper() if name else False)

                sig = cls._clean_signature(full_text)
                entity_type = EntityType.COMPONENT.value if is_component else EntityType.FUNCTION.value

                entities.append(
                    CodeEntityBase(
                        name=name,
                        entity_type=entity_type,
                        file_path=file_path,
                        start_line=start_l,
                        end_line=end_l,
                        signature=sig,
                        parent_entity=None,
                        docstring=None,
                        metadata_json={
                            "is_async": is_async,
                            "is_exported": is_exported_context,
                            "has_jsx": has_jsx,
                        },
                    )
                )
                return

            # 7. Variable Declarations (const/let with Arrow Functions or Function Expressions)
            if node.type in ["lexical_declaration", "variable_declaration"]:
                for declarator in node.children:
                    if declarator.type == "variable_declarator":
                        name_node = declarator.child_by_field_name("name")
                        val_node = declarator.child_by_field_name("value")

                        if name_node and val_node and val_node.type in ["arrow_function", "function_expression"]:
                            name = cls._node_text(name_node, source_bytes)
                            start_l = node.start_point[0] + 1
                            end_l = node.end_point[0] + 1
                            full_text = cls._node_text(node, source_bytes)

                            is_async = any(c.type == "async" for c in val_node.children)
                            has_jsx = cls._has_jsx_descendant(val_node)
                            is_component = has_jsx or (name[0].isupper() if name else False)

                            sig = cls._clean_signature(full_text)
                            entity_type = EntityType.COMPONENT.value if is_component else EntityType.FUNCTION.value

                            entities.append(
                                CodeEntityBase(
                                    name=name,
                                    entity_type=entity_type,
                                    file_path=file_path,
                                    start_line=start_l,
                                    end_line=end_l,
                                    signature=sig,
                                    parent_entity=None,
                                    docstring=None,
                                    metadata_json={
                                        "is_async": is_async,
                                        "is_arrow": val_node.type == "arrow_function",
                                        "is_exported": is_exported_context,
                                        "has_jsx": has_jsx,
                                    },
                                )
                            )
                return

            # Recursively traverse top children
            for child in node.children:
                traverse(child, is_exported_context=is_exported_context, parent_class=parent_class)

        # Execute root traversal
        traverse(tree.root_node)

        # Insert Module Entity at index 0
        module_entity = CodeEntityBase(
            name=Path(file_path).stem,
            entity_type=EntityType.MODULE.value,
            file_path=file_path,
            start_line=1,
            end_line=total_lines,
            signature=f"module {Path(file_path).name}",
            docstring=None,
            metadata_json={
                "imports": imports,
                "total_lines": total_lines,
                "entities_found": len(entities),
            },
        )
        entities.insert(0, module_entity)

        return entities
