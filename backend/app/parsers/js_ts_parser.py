import re
from typing import Any, Dict, List, Optional

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


class JsTsParser(BaseParser):
    def parse(self, file_path: str, relative_path: str, content: str) -> ParsedFile:
        lines = content.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(
            1 for line in lines if line.strip().startswith("//") or line.strip().startswith("/*") or line.strip().startswith("*")
        )

        is_ts = file_path.endswith((".ts", ".tsx"))
        language = "TypeScript" if is_ts else "JavaScript"

        parsed = ParsedFile(
            file_path=file_path,
            relative_path=relative_path,
            language=language,
            lines_of_code=total_lines - blank_lines - comment_lines,
            blank_lines=blank_lines,
            comment_lines=comment_lines,
        )

        self._parse_imports(content, parsed)
        self._parse_classes(content, lines, parsed)
        self._parse_interfaces(content, lines, parsed)
        self._parse_functions(content, lines, parsed)
        self._parse_express_apis(content, lines, parsed)
        self._parse_nextjs_apis(content, lines, relative_path, parsed)
        self._parse_db_models(content, lines, parsed)
        self._parse_exports(content, parsed)

        return parsed

    def _parse_imports(self, content: str, parsed: ParsedFile) -> None:
        # ES6: import { a, b } from './module'; or import React from 'react';
        import_pattern = re.compile(
            r'import\s+(?:(?:\*\s+as\s+(\w+)|(\w+)|(?:\{\s*([^}]+)\s*\}))\s*,\s*)?(?:(\w+)|(?:\{\s*([^}]+)\s*\}))?\s*from\s*[\'"]([^\'"]+)[\'"]'
        )
        for match in import_pattern.finditer(content):
            module_name = match.group(6)
            named_parts = match.group(3) or match.group(5) or ""
            names = [n.strip().split(" as ")[0].strip() for n in named_parts.split(",") if n.strip()]
            default_import = match.group(2) or match.group(4)
            if default_import:
                names.append(default_import)

            parsed.imports.append(
                ImportItem(
                    module=module_name,
                    imported_names=names,
                    is_relative=module_name.startswith("."),
                )
            )

        # CommonJS: const x = require('x');
        require_pattern = re.compile(r'(?:const|let|var)\s+(\{?[^}=]+\}?)\s*=\s*require\([\'"]([^\'"]+)[\'"]\)')
        for match in require_pattern.finditer(content):
            lhs = match.group(1).strip()
            module_name = match.group(2)
            names = [n.strip() for n in lhs.strip("{}").split(",") if n.strip()]
            parsed.imports.append(
                ImportItem(
                    module=module_name,
                    imported_names=names,
                    is_relative=module_name.startswith("."),
                )
            )

    def _parse_classes(self, content: str, lines: List[str], parsed: ParsedFile) -> None:
        class_pattern = re.compile(r'class\s+([A-Za-z0-9_$]+)(?:\s+extends\s+([A-Za-z0-9_$.]+))?(?:\s+implements\s+([A-Za-z0-9_$,\s]+))?')
        for idx, line in enumerate(lines, start=1):
            match = class_pattern.search(line)
            if match:
                class_name = match.group(1)
                parsed.classes.append(
                    CodeSymbol(
                        name=class_name,
                        symbol_type="class",
                        start_line=idx,
                        end_line=idx,
                    )
                )

    def _parse_interfaces(self, content: str, lines: List[str], parsed: ParsedFile) -> None:
        interface_pattern = re.compile(r'(?:interface|type)\s+([A-Za-z0-9_$]+)')
        for idx, line in enumerate(lines, start=1):
            match = interface_pattern.search(line)
            if match:
                name = match.group(1)
                parsed.interfaces.append(
                    CodeSymbol(
                        name=name,
                        symbol_type="interface",
                        start_line=idx,
                        end_line=idx,
                    )
                )

    def _parse_functions(self, content: str, lines: List[str], parsed: ParsedFile) -> None:
        # Standard: function foo(...) or async function foo(...)
        fn_pattern = re.compile(r'(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\)')
        # Arrow: const foo = (...) => or const foo: React.FC = (...) =>
        arrow_pattern = re.compile(r'(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)(?:\s*:\s*[^=]+)?\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>')

        for idx, line in enumerate(lines, start=1):
            fn_match = fn_pattern.search(line)
            if fn_match:
                name = fn_match.group(1)
                params_str = fn_match.group(2)
                params = [ParameterItem(name=p.strip().split(":")[0].strip()) for p in params_str.split(",") if p.strip()]
                is_async = "async" in line
                parsed.functions.append(
                    CodeSymbol(
                        name=name,
                        symbol_type="async_function" if is_async else "function",
                        start_line=idx,
                        end_line=idx,
                        parameters=params,
                    )
                )
                continue

            arrow_match = arrow_pattern.search(line)
            if arrow_match:
                name = arrow_match.group(1)
                params_str = arrow_match.group(2)
                params = [ParameterItem(name=p.strip().split(":")[0].strip()) for p in params_str.split(",") if p.strip()]
                is_async = "async" in line
                parsed.functions.append(
                    CodeSymbol(
                        name=name,
                        symbol_type="async_function" if is_async else "function",
                        start_line=idx,
                        end_line=idx,
                        parameters=params,
                    )
                )

    def _parse_express_apis(self, content: str, lines: List[str], parsed: ParsedFile) -> None:
        # app.get('/users', handler) or router.post('/login', authMiddleware, handler)
        route_pattern = re.compile(r'(?:app|router)\.(get|post|put|delete|patch|options)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]')
        for idx, line in enumerate(lines, start=1):
            match = route_pattern.search(line)
            if match:
                method = match.group(1).upper()
                path = match.group(2)
                auth_required = any(k in line.lower() for k in ["auth", "jwt", "protect", "token", "verify"])
                parsed.apis.append(
                    APIEndpoint(
                        method=method,
                        path=path,
                        handler_name=f"express_{method.lower()}_{path.replace('/', '_').strip('_')}",
                        start_line=idx,
                        auth_required=auth_required,
                        framework="Express",
                    )
                )

    def _parse_nextjs_apis(self, content: str, lines: List[str], relative_path: str, parsed: ParsedFile) -> None:
        # Next.js App Router: export async function GET(request: Request)
        if "api/" in relative_path or "route." in relative_path:
            next_pattern = re.compile(r'export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)\s*\(')
            for idx, line in enumerate(lines, start=1):
                match = next_pattern.search(line)
                if match:
                    method = match.group(1).upper()
                    # Derive route path from file path
                    path = "/" + "/".join(
                        p for p in relative_path.replace("\\", "/").split("/") if p not in ["src", "app", "pages", "api", "route.ts", "route.js"]
                    )
                    parsed.apis.append(
                        APIEndpoint(
                            method=method,
                            path=path or "/",
                            handler_name=f"next_{method.lower()}",
                            start_line=idx,
                            framework="Next.js",
                        )
                    )

    def _parse_db_models(self, content: str, lines: List[str], parsed: ParsedFile) -> None:
        # Mongoose Schema: const UserSchema = new Schema({ ... })
        mongoose_pattern = re.compile(r'(?:const|let|var)\s+([A-Za-z0-9_]+)Schema\s*=\s*new\s*(?:mongoose\.)?Schema\s*\(\{')
        for idx, line in enumerate(lines, start=1):
            match = mongoose_pattern.search(line)
            if match:
                name = match.group(1)
                parsed.db_models.append(
                    DatabaseModel(
                        name=name,
                        table_name=name.lower() + "s",
                        fields=[DBField(name="_id", data_type="ObjectId", is_primary_key=True)],
                        orm_type="Mongoose",
                        start_line=idx,
                    )
                )

    def _parse_exports(self, content: str, parsed: ParsedFile) -> None:
        export_named = re.findall(r'export\s+(?:default\s+)?(?:const|let|var|function|class)\s+([A-Za-z0-9_$]+)', content)
        parsed.exports.extend(export_named)
