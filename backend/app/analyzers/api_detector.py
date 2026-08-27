import ast
import re
from pathlib import Path
from typing import List, Dict, Optional, Any, Set, Tuple
from backend.app.core.logging import logger
from backend.app.schemas.api_endpoint import (
    ApiEndpointBase,
    ApiRequestSchema,
    ApiResponseSchema,
    ApiParameter,
)
from backend.app.analyzers.code_parser import PYTHON_EXTENSIONS, JS_TS_EXTENSIONS


AUTH_KEYWORDS = {
    "auth",
    "token",
    "jwt",
    "security",
    "login",
    "session",
    "permission",
    "oauth",
    "bearer",
    "current_user",
    "get_current_user",
    "get_active_user",
    "api_key",
    "authenticated",
    "require_auth",
    "protect",
}

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}


class ApiDetector:
    @staticmethod
    def _read_file(file_path: Path) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None

    @classmethod
    def detect_apis(cls, repo_dir: Path) -> List[ApiEndpointBase]:
        endpoints: List[ApiEndpointBase] = []

        for path in repo_dir.rglob("*"):
            if not path.is_file():
                continue

            rel_path = str(path.relative_to(repo_dir)).replace("\\", "/")

            # Skip common ignore directories
            parts = Path(rel_path).parts
            if any(p.startswith(".") or p in ["node_modules", "dist", "build", "venv", ".venv", "__pycache__"] for p in parts):
                continue

            ext = path.suffix.lower()

            if ext in PYTHON_EXTENSIONS:
                content = cls._read_file(path)
                if content:
                    # Check for FastAPI / Flask
                    py_endpoints = cls._parse_python_apis(content, rel_path)
                    endpoints.extend(py_endpoints)

            elif ext in JS_TS_EXTENSIONS:
                content = cls._read_file(path)
                if content:
                    # Check for Express
                    js_endpoints = cls._parse_express_apis(content, rel_path)
                    endpoints.extend(js_endpoints)

        return endpoints

    # =========================================================================
    # 1. Python API Parser (FastAPI & Flask)
    # =========================================================================

    @classmethod
    def _parse_python_apis(cls, content: str, file_path: str) -> List[ApiEndpointBase]:
        endpoints: List[ApiEndpointBase] = []
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            return endpoints

        # Scan for APIRouter prefixes and router tags
        router_prefixes: Dict[str, str] = {}
        router_tags: Dict[str, List[str]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                        func_name = ""
                        if isinstance(node.value.func, ast.Name):
                            func_name = node.value.func.id
                        elif isinstance(node.value.func, ast.Attribute):
                            func_name = node.value.func.attr

                        if func_name in ["APIRouter", "Blueprint"]:
                            var_name = target.id
                            prefix = ""
                            tags: List[str] = []

                            # Inspect args & keywords
                            for kw in node.value.keywords:
                                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                    prefix = kw.value.value
                                elif kw.arg == "tags" and isinstance(kw.value, ast.List):
                                    for elt in kw.value.elts:
                                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                            tags.append(elt.value)

                            # First arg for Blueprint
                            if not prefix and node.value.args and len(node.value.args) >= 2:
                                if isinstance(node.value.args[1], ast.Constant) and isinstance(node.value.args[1].value, str):
                                    pass

                            router_prefixes[var_name] = prefix
                            router_tags[var_name] = tags

        # Scan Function Definitions for Route Decorators
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    # 1. FastAPI decorator: @router.get("/path"), @app.post("/path")
                    if isinstance(dec, ast.Call):
                        dec_func = dec.func
                        caller_name = ""
                        method_name = ""

                        if isinstance(dec_func, ast.Attribute):
                            if isinstance(dec_func.value, ast.Name):
                                caller_name = dec_func.value.id
                            method_name = dec_func.attr.lower()

                        if method_name in HTTP_METHODS or method_name == "api_route" or method_name == "route":
                            endpoint = cls._extract_fastapi_or_flask_endpoint(
                                node=node,
                                dec=dec,
                                caller_name=caller_name,
                                method_name=method_name,
                                router_prefixes=router_prefixes,
                                router_tags=router_tags,
                                file_path=file_path,
                            )
                            if endpoint:
                                endpoints.append(endpoint)

        return endpoints

    @classmethod
    def _extract_fastapi_or_flask_endpoint(
        cls,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        dec: ast.Call,
        caller_name: str,
        method_name: str,
        router_prefixes: Dict[str, str],
        router_tags: Dict[str, List[str]],
        file_path: str,
    ) -> Optional[ApiEndpointBase]:
        # Determine framework: FastAPI vs Flask
        is_flask = False
        methods = [method_name.upper()] if method_name in HTTP_METHODS else []

        route_path = ""
        if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
            route_path = dec.args[0].value

        summary: Optional[str] = None
        response_model: Optional[str] = None
        status_code: Optional[int] = 200
        tags: List[str] = list(router_tags.get(caller_name, []))
        auth_required = False

        for kw in dec.keywords:
            if kw.arg == "methods" and isinstance(kw.value, ast.List):
                is_flask = True
                methods = []
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        methods.append(elt.value.upper())
            elif kw.arg == "response_model":
                if isinstance(kw.value, ast.Name):
                    response_model = kw.value.id
                elif isinstance(kw.value, ast.Attribute):
                    response_model = kw.value.attr
            elif kw.arg == "summary" and isinstance(kw.value, ast.Constant):
                summary = str(kw.value.value)
            elif kw.arg == "status_code" and isinstance(kw.value, ast.Constant):
                if isinstance(kw.value.value, int):
                    status_code = kw.value.value
            elif kw.arg == "tags" and isinstance(kw.value, ast.List):
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        if elt.value not in tags:
                            tags.append(elt.value)

        # Check other decorators on the function for auth
        for other_dec in node.decorator_list:
            dec_str = ast.unparse(other_dec).lower()
            if any(k in dec_str for k in ["jwt_required", "login_required", "auth_required", "roles_required"]):
                auth_required = True
                is_flask = True

        # Combine router prefix
        prefix = router_prefixes.get(caller_name, "")
        if prefix:
            combined_path = f"/{prefix.strip('/')}/{route_path.lstrip('/')}".rstrip("/")
            if not combined_path:
                combined_path = "/"
        else:
            combined_path = route_path if route_path.startswith("/") else f"/{route_path}"

        if not combined_path:
            combined_path = "/"

        # Inspect parameters
        parameters: List[ApiParameter] = []
        body_model: Optional[str] = None
        path_variables = set(re.findall(r"\{([A-Za-z0-9_]+)\}", combined_path))
        # Also Flask style <int:user_id> or <user_id>
        flask_vars = re.findall(r"<(?:\w+:)?([A-Za-z0-9_]+)>", combined_path)
        path_variables.update(flask_vars)

        for arg in node.args.args:
            arg_name = arg.arg
            if arg_name in ["self", "cls"]:
                continue

            param_type: Optional[str] = None
            if arg.annotation:
                param_type = ast.unparse(arg.annotation)

            in_loc = "query"
            if arg_name in path_variables:
                in_loc = "path"

            # Check if default is Depends / Security
            is_dep = False
            # Find default
            # In Python AST, defaults align to the end of args
            num_args = len(node.args.args)
            num_defaults = len(node.args.defaults)
            default_val: Optional[str] = None

            arg_idx = node.args.args.index(arg)
            default_offset = num_args - num_defaults
            if arg_idx >= default_offset:
                def_node = node.args.defaults[arg_idx - default_offset]
                default_val = ast.unparse(def_node)
                def_str = default_val.lower()

                if "depends" in def_str or "security" in def_str:
                    is_dep = True
                    in_loc = "dependency"
                    if any(k in def_str for k in AUTH_KEYWORDS):
                        auth_required = True

            # If param type looks like Pydantic model (Capitalized, not in primitives)
            if not is_dep and in_loc != "path" and param_type and param_type[0].isupper() and param_type not in ["Optional", "List", "Dict", "Union", "Set", "Tuple"]:
                if "schema" in param_type.lower() or "create" in param_type.lower() or "update" in param_type.lower() or "request" in param_type.lower() or "model" in param_type.lower() or "data" in param_type.lower():
                    in_loc = "body"
                    body_model = param_type

            parameters.append(
                ApiParameter(
                    name=arg_name,
                    in_location=in_loc,
                    type=param_type,
                    required=(default_val is None),
                    default=default_val,
                )
            )

        # Return type annotation
        return_type = ast.unparse(node.returns) if node.returns else None
        if not response_model and return_type and return_type[0].isupper():
            response_model = return_type

        # Extract docstring
        docstring = ast.get_docstring(node)
        if not summary and docstring:
            summary = docstring.strip().split("\n")[0]

        method = methods[0] if methods else "GET"
        framework = "Flask" if is_flask else "FastAPI"

        return ApiEndpointBase(
            method=method,
            path=combined_path,
            handler_name=node.name,
            file_path=file_path,
            line_number=node.lineno,
            framework=framework,
            request_schema=ApiRequestSchema(
                parameters=parameters,
                body_model=body_model,
            ),
            response_schema=ApiResponseSchema(
                status_code=status_code,
                response_model=response_model,
                return_type=return_type,
            ),
            authentication_required=auth_required,
            tags=tags,
            summary=summary,
            docstring=docstring,
            metadata_json={
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "router_variable": caller_name,
                "status_code": status_code,
            },
        )

    # =========================================================================
    # 2. JavaScript / TypeScript Express API Parser
    # =========================================================================

    @classmethod
    def _parse_express_apis(cls, content: str, file_path: str) -> List[ApiEndpointBase]:
        endpoints: List[ApiEndpointBase] = []

        # Regex for Express route calls: router.get('/users', authMiddleware, controller)
        route_pattern = re.compile(
            r"""(?:router|app)\.(get|post|put|delete|patch|options|all)\s*\(\s*['"]([^'"]+)['"]\s*,\s*([^)]+)\)""",
            re.MULTILINE | re.IGNORECASE,
        )

        for match in route_pattern.finditer(content):
            method_raw = match.group(1).upper()
            path_raw = match.group(2)
            args_raw = match.group(3)

            method = "GET" if method_raw == "ALL" else method_raw

            # Normalize Express :param to {param}
            normalized_path = re.sub(r":([A-Za-z0-9_]+)", r"{\1}", path_raw)
            if not normalized_path.startswith("/"):
                normalized_path = f"/{normalized_path}"

            # Inspect arguments for handlers & auth middlewares
            arg_tokens = [a.strip() for a in args_raw.split(",") if a.strip()]
            handler_name = arg_tokens[-1] if arg_tokens else "anonymousHandler"

            # Clean handler name if it is arrow function or controller.method
            if "=>" in handler_name or "function" in handler_name:
                handler_name = f"handler_{method.lower()}_{path_raw.replace('/', '_').strip('_')}"
            else:
                handler_name = handler_name.split("(")[0].strip()

            auth_required = any(
                any(k in token.lower() for k in AUTH_KEYWORDS) for token in arg_tokens[:-1]
            )

            # Path parameters
            path_params = re.findall(r"\{([A-Za-z0-9_]+)\}", normalized_path)
            parameters = [
                ApiParameter(name=p, in_location="path", type="string", required=True)
                for p in path_params
            ]

            endpoints.append(
                ApiEndpointBase(
                    method=method,
                    path=normalized_path,
                    handler_name=handler_name,
                    file_path=file_path,
                    line_number=None,
                    framework="Express",
                    request_schema=ApiRequestSchema(parameters=parameters),
                    response_schema=ApiResponseSchema(status_code=200),
                    authentication_required=auth_required,
                    tags=["Express"],
                    summary=f"Express {method} {normalized_path}",
                    docstring=None,
                    metadata_json={
                        "middleware_count": len(arg_tokens) - 1,
                        "raw_path": path_raw,
                    },
                )
            )

        return endpoints
