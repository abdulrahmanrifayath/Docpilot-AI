import pytest
from app.parsers.code_extractor import code_parsing_engine


def test_python_ast_extractor():
    py_code = """import os
from typing import List, Optional

class BaseService:
    pass

class UserService(BaseService):
    \"\"\"Manages user entities.\"\"\"
    def __init__(self, db: str = 'default'):
        self.db = db

    async def get_user(self, user_id: int) -> dict:
        \"\"\"Fetch user by ID.\"\"\"
        return {"id": user_id}

def calculate_hash(data: str, salt: Optional[str] = None) -> str:
    \"\"\"Compute SHA-256 hash.\"\"\"
    return "abc"
"""

    entities = code_parsing_engine.parse_file("app/services/user_service.py", py_code)
    type_map = {e.name: e for e in entities}

    # Module
    assert "user_service" in type_map
    assert type_map["user_service"].entity_type == "MODULE"
    assert len(type_map["user_service"].metadata.get("imports", [])) == 2

    # Classes
    assert "BaseService" in type_map
    assert type_map["BaseService"].entity_type == "CLASS"

    assert "UserService" in type_map
    assert type_map["UserService"].entity_type == "CLASS"
    assert type_map["UserService"].metadata.get("inheritance") == ["BaseService"]
    assert type_map["UserService"].metadata.get("docstring") == "Manages user entities."

    # Methods
    assert "__init__" in type_map
    assert type_map["__init__"].entity_type == "METHOD"
    assert type_map["__init__"].parent_entity == "UserService"

    assert "get_user" in type_map
    assert type_map["get_user"].entity_type == "METHOD"
    assert type_map["get_user"].parent_entity == "UserService"
    assert type_map["get_user"].metadata.get("is_async") is True
    assert "async def get_user" in type_map["get_user"].signature

    # Function
    assert "calculate_hash" in type_map
    assert type_map["calculate_hash"].entity_type == "FUNCTION"
    assert type_map["calculate_hash"].parent_entity is None
    assert "salt: Optional[str]" in type_map["calculate_hash"].signature


def test_typescript_tree_sitter_extractor():
    ts_code = """import React from 'react';

export interface UserProps {
    id: string;
    name: string;
}

export class UserStore {
    fetchUsers(): UserProps[] {
        return [];
    }
}

export const UserCard: React.FC<UserProps> = ({ id, name }) => {
    return <div className="card">{name}</div>;
};

export function formatUserName(user: UserProps): string {
    return user.name.toUpperCase();
}
"""

    entities = code_parsing_engine.parse_file("src/components/UserCard.tsx", ts_code)
    type_map = {e.name: e for e in entities}

    # Module
    assert "UserCard" in type_map or "src" in str(entities)

    # Interface
    assert "UserProps" in type_map
    assert type_map["UserProps"].entity_type == "INTERFACE"

    # Class
    assert "UserStore" in type_map
    assert type_map["UserStore"].entity_type == "CLASS"

    # Method
    assert "fetchUsers" in type_map
    assert type_map["fetchUsers"].entity_type == "METHOD"
    assert type_map["fetchUsers"].parent_entity == "UserStore"

    # Component
    assert "UserCard" in type_map
    assert type_map["UserCard"].entity_type in {"COMPONENT", "FUNCTION"}

    # Function
    assert "formatUserName" in type_map
    assert type_map["formatUserName"].entity_type == "FUNCTION"
