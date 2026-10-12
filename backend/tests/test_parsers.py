import pytest
from app.parsers.python_parser import PythonParser
from app.parsers.js_ts_parser import JsTsParser


def test_python_parser_ast():
    sample_code = '''
from fastapi import FastAPI, Depends
from sqlalchemy import Column, Integer, String
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)

app = FastAPI()

@app.get("/api/users")
async def list_users(limit: int = 10):
    """Retrieve all active users."""
    return []
'''
    parser = PythonParser()
    result = parser.parse("app/routes.py", "app/routes.py", sample_code)

    assert result.language == "Python"
    assert len(result.classes) == 1
    assert result.classes[0].name == "User"

    # Verify Database Model extraction
    assert len(result.db_models) == 1
    db_model = result.db_models[0]
    assert db_model.name == "User"
    assert db_model.table_name == "users"
    assert any(f.name == "id" and f.is_primary_key for f in db_model.fields)

    # Verify API Endpoint extraction
    assert len(result.apis) == 1
    api = result.apis[0]
    assert api.method == "GET"
    assert api.path == "/api/users"
    assert api.handler_name == "list_users"
    assert "Retrieve all active users" in (api.docstring or "")


def test_js_ts_parser():
    sample_ts = '''
import React, { useState } from 'react';
import axios from 'axios';

interface UserProps {
    id: string;
    name: string;
}

export const UserCard: React.FC<UserProps> = ({ id, name }) => {
    return <div>{name}</div>;
};

export async function fetchUserData(userId: string) {
    return axios.get(`/users/${userId}`);
}
'''
    parser = JsTsParser()
    result = parser.parse("src/components/UserCard.tsx", "src/components/UserCard.tsx", sample_ts)

    assert result.language == "TypeScript"
    assert len(result.interfaces) == 1
    assert result.interfaces[0].name == "UserProps"
    assert len(result.functions) >= 1
    assert any(f.name == "fetchUserData" for f in result.functions)
    assert len(result.imports) == 2
