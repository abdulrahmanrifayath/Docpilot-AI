import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class FunctionCallVisitor(ast.NodeVisitor):
    """Collects all function/class calls and referenced identifiers within a function."""

    def __init__(self) -> None:
        self.calls: Set[str] = set()
        self.names: Set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.add(node.func.attr)
            if isinstance(node.func.value, ast.Name):
                self.calls.add(f"{node.func.value.id}.{node.func.attr}")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self.names.add(node.id)
        self.generic_visit(node)


class AutomaticAPIDiscoveryService:
    """
    Statically analyzes repository source code to discover backend API endpoints.
    Initially supports:
    - Python: FastAPI and Flask
    - JavaScript/TypeScript: Express
    """

    HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}

    AUTH_KEYWORDS = {
        "auth",
        "login",
        "token",
        "jwt",
        "oauth",
        "oauth2",
        "security",
        "api_key",
        "apikey",
        "current_user",
        "user_id",
        "credential",
        "credentials",
        "permission",
        "permissions",
        "role",
        "roles",
        "admin",
        "protect",
        "authenticated",
        "authenticate",
        "verify",
    }

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

    def discover_apis(self, project_root: str) -> List[Dict[str, Any]]:
        """
        Recursively scans the project directory and returns all detected API endpoints.
        """
        root_path = Path(project_root)
        if not root_path.exists() or not root_path.is_dir():
            return []

        discovered: List[Dict[str, Any]] = []

        for dirpath, dirnames, filenames in os.walk(str(root_path)):
            # Prune ignored directories
            dirnames[:] = [d for d in dirnames if d not in self.IGNORE_DIRS and not d.startswith(".")]

            for filename in filenames:
                file_path = Path(dirpath) / filename
                rel_path = file_path.relative_to(root_path).as_posix()

                if filename.endswith(".py"):
                    endpoints = self._discover_python_apis(file_path, rel_path)
                    discovered.extend(endpoints)
                elif filename.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
                    endpoints = self._discover_js_ts_apis(file_path, rel_path)
                    discovered.extend(endpoints)

        # Deduplicate endpoints by (method, path, file_path, handler_name)
        unique_endpoints: List[Dict[str, Any]] = []
        seen = set()
        for ep in discovered:
            key = (ep["method"].upper(), ep["path"], ep["file_path"], ep["handler_name"])
            if key not in seen:
                seen.add(key)
                unique_endpoints.append(ep)

        # Sort cleanly by path, then method
        unique_endpoints.sort(key=lambda x: (x["path"], x["method"]))
        return unique_endpoints

    # =========================================================================
    # PYTHON: FastAPI & Flask
    # =========================================================================

    def _discover_python_apis(self, file_path: Path, rel_path: str) -> List[Dict[str, Any]]:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(file_path))
        except Exception:
            return []

        endpoints: List[Dict[str, Any]] = []

        # 1. First pass: extract router and blueprint prefixes and tags
        router_prefixes, router_tags = self._extract_python_router_meta(tree)

        # 2. Second pass: examine function & async function definitions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                eps = self._extract_python_endpoint_from_func(
                    node, rel_path, router_prefixes, router_tags
                )
                endpoints.extend(eps)

        return endpoints

    def _extract_python_router_meta(
        self, tree: ast.AST
    ) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """
        Detects APIRouter(prefix="/...", tags=[...]) and Blueprint('...', __name__, url_prefix='/...')
        """
        router_prefixes: Dict[str, str] = {}
        router_tags: Dict[str, List[str]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        val = node.value
                        if isinstance(val, ast.Call):
                            call_name = self._format_node(val.func)
                            # FastAPI APIRouter
                            if "APIRouter" in call_name:
                                for kw in val.keywords:
                                    if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                                        if isinstance(kw.value.value, str):
                                            router_prefixes[var_name] = kw.value.value
                                    elif kw.arg == "tags" and isinstance(kw.value, (ast.List, ast.Tuple)):
                                        tags = [
                                            elt.value
                                            for elt in kw.value.elts
                                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                                        ]
                                        router_tags[var_name] = tags
                            # Flask Blueprint
                            elif "Blueprint" in call_name:
                                for kw in val.keywords:
                                    if kw.arg == "url_prefix" and isinstance(kw.value, ast.Constant):
                                        if isinstance(kw.value.value, str):
                                            router_prefixes[var_name] = kw.value.value

        return router_prefixes, router_tags

    def _extract_python_endpoint_from_func(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        rel_path: str,
        router_prefixes: Dict[str, str],
        router_tags: Dict[str, List[str]],
    ) -> List[Dict[str, Any]]:
        endpoints: List[Dict[str, Any]] = []

        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue

            dec_func_name = self._format_node(dec.func)
            func_attr = dec_func_name.split(".")[-1].lower()
            caller_var = dec_func_name.split(".")[0] if "." in dec_func_name else ""

            # Detect FastAPI: @app.get(...), @router.post(...), etc.
            # or Flask: @app.route(...), @bp.route(...)
            is_fastapi_method = func_attr in self.HTTP_METHODS
            is_route_decorator = func_attr == "route" or func_attr == "api_route"

            if not (is_fastapi_method or is_route_decorator):
                continue

            # Determine HTTP methods
            methods: List[str] = []
            if is_fastapi_method:
                methods = [func_attr.upper()]
            elif is_route_decorator:
                # Check methods kwarg
                methods_kw = None
                for kw in dec.keywords:
                    if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                        methods_kw = [
                            elt.value.upper()
                            for elt in kw.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ]
                        break
                methods = methods_kw if methods_kw else ["GET"]

            # Determine route path
            raw_path = "/"
            if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                raw_path = dec.args[0].value
            else:
                for kw in dec.keywords:
                    if kw.arg == "path" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        raw_path = kw.value.value
                        break

            # Apply router prefix if present
            prefix = router_prefixes.get(caller_var, "")
            final_path = self._combine_path_prefix(prefix, raw_path)

            # Extract tags
            tags: List[str] = list(router_tags.get(caller_var, []))
            for kw in dec.keywords:
                if kw.arg == "tags" and isinstance(kw.value, (ast.List, ast.Tuple)):
                    dec_tags = [
                        elt.value
                        for elt in kw.value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    ]
                    for t in dec_tags:
                        if t not in tags:
                            tags.append(t)

            if not tags:
                # Derive tag from first path segment
                segments = [s for s in final_path.strip("/").split("/") if s and s not in ("api", "v1", "v2")]
                tags = [segments[0].capitalize() if segments else "Root"]

            # Response schema / model
            response_schema: Dict[str, Any] = {}
            response_model_name = None
            status_code = 200

            for kw in dec.keywords:
                if kw.arg in ("response_model", "response"):
                    response_model_name = self._format_node(kw.value)
                elif kw.arg == "status_code":
                    if isinstance(kw.value, ast.Constant):
                        status_code = int(kw.value.value)
                    else:
                        val_str = self._format_node(kw.value)
                        digits = re.findall(r"\d{3}", val_str)
                        if digits:
                            status_code = int(digits[0])

            return_type = self._format_node(node.returns) if node.returns else None
            if not response_model_name and return_type:
                response_model_name = return_type

            response_schema = {
                "model": response_model_name or "Any",
                "status_code": status_code,
                "return_type": return_type,
            }

            # Dependencies & Authentication Analysis
            dependencies, auth_required = self._analyze_dependencies_and_auth(node, dec)

            # Request schema & parameters
            request_schema = self._extract_python_request_schema(node, final_path)

            # Docstring & Purpose
            docstring = ast.get_docstring(node)
            purpose = (
                docstring.strip().split("\n")[0]
                if docstring
                else "Static analysis detected API endpoint. Purpose documentation will be automatically generated by AI."
            )

            # Calls & Related components inside handler body
            call_visitor = FunctionCallVisitor()
            call_visitor.visit(node)
            related_components = sorted(list(call_visitor.calls))

            framework = "Flask" if is_route_decorator and not is_fastapi_method else "FastAPI"
            if "router" in caller_var.lower() or "fastapi" in caller_var.lower():
                framework = "FastAPI"

            for method in methods:
                endpoints.append({
                    "method": method,
                    "path": final_path,
                    "handler_name": node.name,
                    "file_path": rel_path,
                    "request_schema": request_schema,
                    "response_schema": response_schema,
                    "authentication_required": auth_required,
                    "tags": tags,
                    "metadata": {
                        "start_line": node.lineno,
                        "end_line": getattr(node, "end_lineno", node.lineno),
                        "framework": framework,
                        "docstring": docstring,
                        "purpose": purpose,
                        "dependencies": dependencies,
                        "router_variable": caller_var or None,
                        "related_components": related_components,
                    },
                })

        return endpoints

    def _analyze_dependencies_and_auth(
        self,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        dec_call: ast.Call,
    ) -> Tuple[List[str], bool]:
        """
        Detects Depends(...) in parameters, decorator dependencies, and determines authentication.
        """
        dependencies: List[str] = []
        auth_required = False

        # 1. Check decorators for auth decorators: @login_required, @jwt_required, etc.
        for d in func_node.decorator_list:
            d_str = self._format_node(d).lower()
            if any(k in d_str for k in ("login_required", "jwt_required", "auth_required", "roles_accepted")):
                auth_required = True

        # 2. Check decorator dependencies kwarg: dependencies=[Depends(get_current_user)]
        for kw in dec_call.keywords:
            if kw.arg == "dependencies" and isinstance(kw.value, (ast.List, ast.Tuple)):
                for elt in kw.value.elts:
                    dep_name = self._format_node(elt)
                    dependencies.append(dep_name)
                    if any(k in dep_name.lower() for k in self.AUTH_KEYWORDS):
                        auth_required = True

        # 3. Check function parameters
        # Combine args + kwonlyargs
        all_args = list(func_node.args.args) + list(func_node.args.kwonlyargs)
        # Defaults alignment for positional args
        defaults = [None] * (len(func_node.args.args) - len(func_node.args.defaults)) + list(
            func_node.args.defaults
        )
        kw_defaults = func_node.args.kw_defaults

        all_defaults = defaults + kw_defaults

        for arg, default_val in zip(all_args, all_defaults):
            if arg.arg in ("self", "cls"):
                continue

            param_name = arg.arg
            type_hint = self._format_node(arg.annotation) if arg.annotation else ""

            # Check if default is Depends(...) or Security(...)
            if default_val is not None:
                default_str = self._format_node(default_val)
                if "Depends" in default_str or "Security" in default_str:
                    dependencies.append(f"{param_name}: {default_str}")
                    if any(k in default_str.lower() for k in self.AUTH_KEYWORDS):
                        auth_required = True

            # Check parameter name or type hint for auth
            if any(k in param_name.lower() for k in self.AUTH_KEYWORDS) and "auth" in param_name.lower():
                auth_required = True
            if any(k in type_hint.lower() for k in ("user", "token", "credentials", "apikey")):
                # Check if it's a security/auth parameter
                if "user" in param_name.lower() or "auth" in param_name.lower():
                    auth_required = True

        return dependencies, auth_required

    def _extract_python_request_schema(
        self,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        path: str,
    ) -> Dict[str, Any]:
        """
        Categorizes parameters into path, query, body, and header parameters.
        """
        path_params_set = set(re.findall(r"\{([a-zA-Z0-9_]+)\}", path))
        flask_path_params = set(re.findall(r"<(?:\w+:)?([a-zA-Z0-9_]+)>", path))
        path_params_set.update(flask_path_params)

        parameters: List[Dict[str, Any]] = []
        body_model: Optional[str] = None

        primitive_types = {
            "int", "str", "float", "bool", "bytes", "list", "dict", "set", "tuple",
            "optional[int]", "optional[str]", "optional[float]", "optional[bool]",
        }

        system_types = {
            "request", "response", "backgroundtasks", "session", "db",
            "websocket", "fastapi.request", "fastapi.response"
        }

        all_args = list(func_node.args.args) + list(func_node.args.kwonlyargs)
        defaults = [None] * (len(func_node.args.args) - len(func_node.args.defaults)) + list(
            func_node.args.defaults
        )
        all_defaults = defaults + func_node.args.kw_defaults

        for arg, default_val in zip(all_args, all_defaults):
            if arg.arg in ("self", "cls"):
                continue

            name = arg.arg
            type_hint = self._format_node(arg.annotation) if arg.annotation else "Any"
            type_lower = type_hint.lower()
            default_str = self._format_node(default_val) if default_val else None

            # Skip DI dependencies
            if default_str and ("Depends" in default_str or "Security" in default_str):
                continue
            if type_lower in system_types:
                continue

            # Determine parameter location
            if name in path_params_set:
                param_in = "path"
                required = True
            elif default_str and "Header" in default_str:
                param_in = "header"
                required = "..." in default_str or default_str == "Header()"
            elif default_str and "Query" in default_str:
                param_in = "query"
                required = "..." in default_str
            elif default_str and "Body" in default_str:
                param_in = "body"
                required = "..." in default_str
                body_model = type_hint
            elif type_lower in primitive_types or "optional" in type_lower or default_str is not None:
                param_in = "query"
                required = default_str is None
            else:
                # Likely a Pydantic Request Body model!
                param_in = "body"
                required = default_str is None
                body_model = type_hint

            parameters.append({
                "name": name,
                "type": type_hint,
                "in": param_in,
                "required": required,
                "default": default_str if default_str and "..." not in default_str else None,
            })

        return {
            "body_model": body_model,
            "body_type": "application/json" if body_model else None,
            "parameters": parameters,
        }

    # =========================================================================
    # JAVASCRIPT / TYPESCRIPT: Express
    # =========================================================================

    def _discover_js_ts_apis(self, file_path: Path, rel_path: str) -> List[Dict[str, Any]]:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return []

        endpoints: List[Dict[str, Any]] = []
        lines = content.splitlines()

        # Express Route Pattern:
        # app.get('/users', authMiddleware, userController.getUsers)
        # router.post('/login', validate(loginSchema), (req, res) => ...)
        route_regex = re.compile(
            r'(?:app|router)\.(get|post|put|delete|patch|options|head)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]\s*,\s*([\s\S]*?)(?:\);|$)',
            re.MULTILINE,
        )

        for match in route_regex.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            handlers_text = match.group(3).strip()

            # Find line number
            start_pos = match.start()
            start_line = content[:start_pos].count("\n") + 1

            # Extract handler name and middleware arguments
            handler_name, middlewares = self._parse_express_handlers(handlers_text, method, path)

            # Check authentication indicators in middlewares
            auth_required = any(
                any(k in m.lower() for k in self.AUTH_KEYWORDS)
                for m in middlewares
            )

            # Path parameters from :id or :user_id
            path_params = re.findall(r":([a-zA-Z0-9_]+)", path)
            parameters = [
                {"name": p, "type": "string", "in": "path", "required": True}
                for p in path_params
            ]

            # Request / Response schemas
            request_schema = {
                "body_model": None,
                "body_type": "application/json" if method in ("POST", "PUT", "PATCH") else None,
                "parameters": parameters,
            }

            response_schema = {
                "model": "JSON",
                "status_code": 201 if method == "POST" else 200,
                "return_type": "Response",
            }

            segments = [s for s in path.strip("/").split("/") if s and not s.startswith(":") and s not in ("api", "v1", "v2")]
            tag = segments[0].capitalize() if segments else "Root"

            endpoints.append({
                "method": method,
                "path": path,
                "handler_name": handler_name,
                "file_path": rel_path,
                "request_schema": request_schema,
                "response_schema": response_schema,
                "authentication_required": auth_required,
                "tags": [tag],
                "metadata": {
                    "start_line": start_line,
                    "end_line": start_line,
                    "framework": "Express",
                    "purpose": f"Express {method} endpoint handling {path}.",
                    "middlewares": middlewares,
                    "related_components": [handler_name] if handler_name else [],
                },
            })

        return endpoints

    def _parse_express_handlers(
        self, handlers_text: str, method: str, path: str
    ) -> Tuple[str, List[str]]:
        """
        Parses comma-separated middleware arguments in an Express route.
        e.g. 'authMiddleware, validate(schema), UserController.getUsers'
        """
        # Split by comma at top level
        parts = [p.strip() for p in handlers_text.split(",") if p.strip()]
        if not parts:
            default_handler = f"express_{method.lower()}_{path.replace('/', '_').replace(':', '').strip('_')}"
            return default_handler, []

        middlewares: List[str] = []
        handler_name = ""

        # Last item is usually the main controller/handler function
        last_item = parts[-1]
        if "=>" in last_item or "function" in last_item:
            # Anonymous function
            clean_path = path.replace("/", "_").replace(":", "").strip("_") or "root"
            handler_name = f"{method.lower()}_{clean_path}_handler"
        else:
            handler_name = last_item.split("(")[0].strip()

        # Prior items are middlewares
        for m in parts[:-1]:
            clean_m = m.split("(")[0].strip()
            middlewares.append(clean_m)

        return handler_name, middlewares

    # =========================================================================
    # Helpers
    # =========================================================================

    def _combine_path_prefix(self, prefix: str, path: str) -> str:
        if not prefix:
            return path if path.startswith("/") else f"/{path}"
        prefix_clean = "/" + prefix.strip("/")
        path_clean = path.strip("/")
        if not path_clean:
            return prefix_clean
        return f"{prefix_clean}/{path_clean}"

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
        elif isinstance(node, ast.List):
            return f"[{', '.join(self._format_node(e) for e in node.elts)}]"
        elif isinstance(node, ast.Tuple):
            return f"({', '.join(self._format_node(e) for e in node.elts)})"
        return ""
