from pathlib import Path
from app.parsers.base import BaseParser
from app.parsers.python_parser import PythonParser
from app.parsers.js_ts_parser import JsTsParser
from app.parsers.generic_parser import GenericParser

_python_parser = PythonParser()
_js_ts_parser = JsTsParser()
_generic_parser = GenericParser()


def get_parser(file_path: str) -> BaseParser:
    ext = Path(file_path).suffix.lower()
    if ext == ".py":
        return _python_parser
    elif ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        return _js_ts_parser
    return _generic_parser
