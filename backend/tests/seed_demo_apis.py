from pathlib import Path
import httpx

repo_dir = Path(r"C:\Users\arrah\OneDrive\Documents\GitHub\Docpilot-AI\storage\repos\c921a11b-1776-4a00-9148-5106b23f0454")
routers_dir = repo_dir / "backend" / "app" / "routers"
routers_dir.mkdir(parents=True, exist_ok=True)

# 1. backend/app/main.py
(repo_dir / "backend" / "app" / "main.py").write_text(
    'from fastapi import FastAPI\n'
    'from backend.app.routers import users, projects\n\n'
    'app = FastAPI(title="DocPilot AI API", version="1.0.0")\n\n'
    '@app.get("/api/v1/system/status", summary="Get system health status")\n'
    'def get_system_status():\n'
    '    """Returns system health and active services status."""\n'
    '    return {"status": "healthy"}\n',
    encoding="utf-8"
)

# 2. backend/app/routers/users.py
(routers_dir / "users.py").write_text(
    'from fastapi import APIRouter, Depends, status\n'
    'from typing import List, Optional\n'
    'from pydantic import BaseModel\n\n'
    'class UserResponse(BaseModel):\n'
    '    id: int\n'
    '    username: str\n'
    '    email: str\n\n'
    'class UserCreate(BaseModel):\n'
    '    username: str\n'
    '    email: str\n'
    '    password: str\n\n'
    'router = APIRouter(prefix="/api/v1/users", tags=["Users"])\n\n'
    '@router.get("", response_model=List[UserResponse], summary="List registered users")\n'
    'def list_users(skip: int = 0, limit: int = 100, current_user = Depends(get_current_user)):\n'
    '    """Retrieve paginated list of registered users in the organization."""\n'
    '    return []\n\n'
    '@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")\n'
    'def get_user_by_id(user_id: int, current_user = Depends(get_current_user)):\n'
    '    """Retrieve detailed profile of a user by primary key ID."""\n'
    '    return {"id": user_id, "username": "admin", "email": "admin@docpilot.ai"}\n\n'
    '@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create new user account")\n'
    'def create_user(payload: UserCreate):\n'
    '    """Create a new user account with validated credentials."""\n'
    '    return {"id": 1, "username": payload.username, "email": payload.email}\n',
    encoding="utf-8"
)

# 3. backend/app/routers/projects.py
(routers_dir / "projects.py").write_text(
    'from fastapi import APIRouter, Depends, status\n'
    'from typing import List, Optional\n'
    'from pydantic import BaseModel\n\n'
    'class ProjectResponse(BaseModel):\n'
    '    id: str\n'
    '    name: str\n'
    '    status: str\n\n'
    'class ProjectCreate(BaseModel):\n'
    '    name: str\n'
    '    description: Optional[str] = None\n\n'
    'router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])\n\n'
    '@router.get("", response_model=List[ProjectResponse], summary="List workspace projects")\n'
    'def list_projects(skip: int = 0, limit: int = 50, current_user = Depends(get_current_user)):\n'
    '    """Returns all workspace repositories for active tenant."""\n'
    '    return []\n\n'
    '@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="Register project")\n'
    'def create_project(data: ProjectCreate, current_user = Depends(get_current_user)):\n'
    '    """Registers a new project repository for AST and AI analysis."""\n'
    '    return {"id": "p1", "name": data.name, "status": "CREATED"}\n\n'
    '@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete project")\n'
    'def delete_project(project_id: str, current_user = Depends(get_current_user)):\n'
    '    """Deletes a project and removes its local repository files."""\n'
    '    pass\n',
    encoding="utf-8"
)

# 4. Trigger analyze
client = httpx.Client(base_url="http://127.0.0.1:8000")
res = client.post("/api/v1/projects/c921a11b-1776-4a00-9148-5106b23f0454/apis/analyze")
print("Analyzed demo project:", res.json())
