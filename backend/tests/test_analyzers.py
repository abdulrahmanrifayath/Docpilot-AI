from pathlib import Path
from app.analyzers.language_detector import LanguageDetector
from app.analyzers.structure_analyzer import StructureAnalyzer
from app.analyzers.api_analyzer import APIAnalyzer
from app.analyzers.database_analyzer import DatabaseAnalyzer
from app.parsers.base import APIEndpoint, DatabaseModel, DBField, ParsedFile


def test_api_analyzer():
    pf = ParsedFile(
        file_path="app/api.py",
        relative_path="app/api.py",
        language="Python",
        apis=[
            APIEndpoint(method="GET", path="/api/items", handler_name="get_items", start_line=10),
            APIEndpoint(method="POST", path="/api/items", handler_name="create_item", start_line=20, auth_required=True),
        ],
    )
    analyzer = APIAnalyzer()
    res = analyzer.analyze([pf])

    assert res["total_endpoints"] == 2
    assert res["authenticated_count"] == 1
    assert res["public_count"] == 1
    assert res["method_distribution"]["GET"] == 1
    assert res["method_distribution"]["POST"] == 1


def test_database_analyzer():
    pf = ParsedFile(
        file_path="app/models.py",
        relative_path="app/models.py",
        language="Python",
        db_models=[
            DatabaseModel(
                name="Order",
                table_name="orders",
                fields=[
                    DBField(name="id", data_type="Integer", is_primary_key=True),
                    DBField(name="user_id", data_type="Integer", is_foreign_key=True, foreign_key_target="users.id"),
                ],
            ),
            DatabaseModel(
                name="User",
                table_name="users",
                fields=[
                    DBField(name="id", data_type="Integer", is_primary_key=True),
                    DBField(name="email", data_type="String"),
                ],
            ),
        ],
    )
    analyzer = DatabaseAnalyzer()
    res = analyzer.analyze([pf])

    assert res["total_models"] == 2
    assert len(res["relationships"]) >= 1
    rel = res["relationships"][0]
    assert rel["source_model"] == "Order"
    assert rel["target_model"] == "User"
