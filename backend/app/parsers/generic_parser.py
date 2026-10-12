import re
from typing import List

from app.parsers.base import BaseParser, CodeSymbol, DatabaseModel, DBField, ParsedFile


class GenericParser(BaseParser):
    def parse(self, file_path: str, relative_path: str, content: str) -> ParsedFile:
        lines = content.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(
            1 for line in lines if line.strip().startswith(("#", "//", "/*", "*", "--", ";"))
        )

        ext = file_path.split(".")[-1].lower() if "." in file_path else ""
        lang_map = {
            "go": "Go",
            "java": "Java",
            "c": "C",
            "cpp": "C++",
            "cs": "C#",
            "rs": "Rust",
            "php": "PHP",
            "rb": "Ruby",
            "sql": "SQL",
            "html": "HTML",
            "css": "CSS",
            "json": "JSON",
            "yaml": "YAML",
            "yml": "YAML",
            "sh": "Shell",
            "md": "Markdown",
        }
        language = lang_map.get(ext, "Plain Text")

        parsed = ParsedFile(
            file_path=file_path,
            relative_path=relative_path,
            language=language,
            lines_of_code=total_lines - blank_lines - comment_lines,
            blank_lines=blank_lines,
            comment_lines=comment_lines,
        )

        # SQL DDL parsing for database analysis
        if ext == "sql":
            self._parse_sql_ddl(content, lines, parsed)

        return parsed

    def _parse_sql_ddl(self, content: str, lines: List[str], parsed: ParsedFile) -> None:
        table_pattern = re.compile(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_"`]+)', re.IGNORECASE)
        for idx, line in enumerate(lines, start=1):
            match = table_pattern.search(line)
            if match:
                tbl_name = match.group(1).strip('`"')
                parsed.db_models.append(
                    DatabaseModel(
                        name=tbl_name.capitalize(),
                        table_name=tbl_name,
                        fields=[DBField(name="id", data_type="INTEGER", is_primary_key=True)],
                        orm_type="SQL",
                        start_line=idx,
                    )
                )
