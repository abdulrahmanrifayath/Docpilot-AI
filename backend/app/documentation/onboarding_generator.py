from typing import Any, Dict, List


class OnboardingGenerator:
    def generate(
        self,
        repo_name: str,
        languages: Dict[str, Any],
        frameworks: List[str],
        structure: Dict[str, Any],
        apis: List[Dict[str, Any]],
        models: List[Dict[str, Any]],
    ) -> str:
        """Generates a developer onboarding guide for engineering teams."""
        top_langs = list(languages.keys())[:3]
        primary_lang = top_langs[0] if top_langs else "Python"

        folder_map = []
        for path, purpose in list(structure.get("folder_purposes", {}).items())[:10]:
            folder_map.append(f"- `/{path}`: {purpose}")
        folder_str = "\n".join(folder_map) or "- `/src`: Primary application code"

        return f"""# 🚀 {repo_name} — Developer Onboarding Guide

> Step-by-step guide to get newly joined developers productive in hours, not weeks.

---

## 🎯 1. Mental Model of the Application

Think of **{repo_name}** as structured around three primary layers:
1. **The Ingress Layer**: Endpoints that accept external requests, authenticate tokens, and parse input parameters.
2. **The Business Services Layer**: Domain logic that enforces application rules and transforms data.
3. **The Data Layer**: Entities and relational models persisted to storage.

---

## 💻 2. Prerequisites & Local Environment

Ensure you have installed:
{chr(10).join([f'- **{lang} Runtime**' for lang in top_langs])}
- **Git**
- Relevant package managers (e.g., `pip` or `npm`)

---

## ⚡ 3. Day 1 Setup Walkthrough

### Step 1: Clone the Codebase
```bash
git clone <repo-url>
cd {repo_name}
```

### Step 2: Configure Environment Variables
Copy the environment template:
```bash
cp .env.example .env
```
Inspect `.env` and verify database and secret credentials for local development.

### Step 3: Install Project Dependencies
{"```bash\n# Python Virtual Environment\npython -m venv .venv\nsource .venv/bin/activate  # On Windows: .venv\\Scripts\\activate\npip install -r requirements.txt\n```" if primary_lang == "Python" else "```bash\n# Node dependencies\nnpm install\n```"}

### Step 4: Run the Test Suite
Ensure all baseline tests pass locally:
{"```bash\npytest\n```" if primary_lang == "Python" else "```bash\nnpm test\n```"}

### Step 5: Start Local Development Server
{"```bash\nuvicorn app.main:app --reload --port 8000\n```" if "FastAPI" in frameworks else ("```bash\nnpm run dev\n```" if "React" in frameworks or "Next.js" in frameworks else "```bash\npython main.py\n```")}

---

## 🗺️ 4. Codebase Navigation Map ("Where is what?")

When looking for specific functionality:
{folder_str}

---

## 🔨 5. Common Developer Workflows

### How to Add a New API Endpoint
1. Locate the appropriate router file (e.g. in `routes/` or `api/`).
2. Define a Pydantic / TypeScript schema for request and response validation.
3. Add the handler function with the desired HTTP method decorator.
4. Delegate complex business logic to a dedicated service class rather than writing it inside the route handler.
5. Add unit and integration tests covering positive and negative status codes.

### How to Add or Modify a Database Model
1. Open the models directory.
2. Define the new entity class inheriting from the Base model.
3. Add fields, types, constraints, and relationships.
4. Run migrations if an ORM migration tool (e.g., Alembic / Prisma) is configured.

### Authentication & Authorization Flow
- Protected routes require authorization tokens in request headers (`Authorization: Bearer <token>`).
- Context is attached to the request session by middleware before the controller executes.

---

## ❓ 6. Frequently Asked Questions & Gotchas

- **Where are application secrets kept?** Never commit secrets to Git. Always use `.env` files.
- **How to format code?** Run linters (`ruff`, `flake8`, `prettier`, or `eslint`) before committing.
- **Need help?** Check the [Architecture Guide](./ARCHITECTURE.md) and [API Reference](./API_REFERENCE.md).
"""
