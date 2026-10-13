import io
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import init_db
from app.services.database_analyzer import database_structure_analyzer


@pytest.mark.asyncio
async def test_database_structure_analyzer_unit():
    # Unit test parsing logic with SQLAlchemy models code
    sample_sa_code = """
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)
    email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)

    orders = relationship("Order", back_populates="user")

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    total_amount = Column(Integer, default=0)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_name = Column(String(100), nullable=False)
"""
    # Create temp in-memory or directory test
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        (p / "models.py").write_text(sample_sa_code, encoding="utf-8")
        
        # Also add a raw SQL file
        sql_content = """
        CREATE TABLE departments (
            dept_id INT PRIMARY KEY,
            dept_name VARCHAR(100) NOT NULL
        );

        CREATE TABLE employees (
            emp_id INT PRIMARY KEY,
            emp_name VARCHAR(100) NOT NULL,
            dept_id INT REFERENCES departments(dept_id)
        );
        """
        (p / "schema.sql").write_text(sql_content, encoding="utf-8")

        result = database_structure_analyzer.analyze_repository(tmpdir)
        
        model_names = [m["name"] for m in result["models"]]
        assert "User" in model_names
        assert "Order" in model_names
        assert "OrderItem" in model_names
        assert "Department" in model_names

        user_model = next(m for m in result["models"] if m["name"] == "User")
        assert user_model["table_name"] == "users"
        id_field = next(f for f in user_model["fields"] if f["name"] == "id")
        assert id_field["is_primary_key"] is True
        assert id_field["data_type"] == "Integer"

        order_model = next(m for m in result["models"] if m["name"] == "Order")
        uid_field = next(f for f in order_model["fields"] if f["name"] == "user_id")
        assert uid_field["is_foreign_key"] is True
        assert uid_field["foreign_key_target"] == "users.id"

        # Check ER diagram generation
        diagram = database_structure_analyzer.generate_mermaid_er(result["models"], result["relationships"])
        assert "erDiagram" in diagram
        assert "USER" in diagram
        assert "ORDER" in diagram


@pytest.mark.asyncio
async def test_full_database_analysis_endpoints_pipeline():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a project
        create_res = await client.post(
            "/api/v1/projects",
            json={
                "name": "Phase 7 Database Analysis Project",
                "description": "SQLAlchemy, Django and SQL schema relationship test",
            },
        )
        assert create_res.status_code == 201
        project_id = create_res.json()["id"]

        # 2. Build multi-ORM project zip
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # SQLAlchemy classic & 2.0 models
            zf.writestr(
                "backend/models/store.py",
                "from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime\n"
                "from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column\n"
                "\n"
                "Base = declarative_base()\n"
                "\n"
                "class Customer(Base):\n"
                "    __tablename__ = 'customers'\n"
                "    id = Column(Integer, primary_key=True)\n"
                "    email = Column(String(120), nullable=False)\n"
                "    is_active = Column(Boolean, default=True)\n"
                "    orders = relationship('CustomerOrder', back_populates='customer')\n"
                "\n"
                "class CustomerOrder(Base):\n"
                "    __tablename__ = 'customer_orders'\n"
                "    id: Mapped[int] = mapped_column(primary_key=True)\n"
                "    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)\n"
                "    total = Column(Integer, default=0)\n"
                "    customer = relationship('Customer', back_populates='orders')\n"
            )

            # Django ORM models
            zf.writestr(
                "backend/django_app/models.py",
                "from django.db import models\n"
                "\n"
                "class Author(models.Model):\n"
                "    name = models.CharField(max_length=100)\n"
                "    bio = models.TextField(blank=True, null=True)\n"
                "\n"
                "class Book(models.Model):\n"
                "    title = models.CharField(max_length=200)\n"
                "    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')\n"
            )

            # Raw SQL schema
            zf.writestr(
                "database/schema.sql",
                "CREATE TABLE roles (\n"
                "    id INT PRIMARY KEY,\n"
                "    role_name VARCHAR(50) NOT NULL\n"
                ");\n"
                "\n"
                "CREATE TABLE user_roles (\n"
                "    user_id INT NOT NULL,\n"
                "    role_id INT REFERENCES roles(id),\n"
                "    PRIMARY KEY (user_id, role_id)\n"
                ");\n"
            )

        zip_buf.seek(0)

        # 3. Upload files to project
        upload_res = await client.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("project_source.zip", zip_buf.getvalue(), "application/zip")},
        )
        assert upload_res.status_code == 200

        # 4. Trigger Database Analysis (POST /database/analyze)
        analyze_res = await client.post(f"/api/v1/projects/{project_id}/database/analyze")
        assert analyze_res.status_code == 200
        analysis_data = analyze_res.json()
        assert analysis_data["status"] == "ANALYZED"
        assert analysis_data["total_models"] >= 5
        assert analysis_data["total_fields"] >= 10
        assert analysis_data["total_relationships"] >= 2
        assert "SQLAlchemy" in analysis_data["orm_breakdown"]
        assert "Django" in analysis_data["orm_breakdown"]
        assert "SQL" in analysis_data["orm_breakdown"]

        # 5. List Database Models (GET /database/models)
        models_res = await client.get(f"/api/v1/projects/{project_id}/database/models")
        assert models_res.status_code == 200
        models_list = models_res.json()
        model_names = [m["name"] for m in models_list]
        assert "Customer" in model_names
        assert "CustomerOrder" in model_names
        assert "Author" in model_names
        assert "Book" in model_names

        # Test filter by ORM type
        sa_models_res = await client.get(f"/api/v1/projects/{project_id}/database/models?orm_type=SQLAlchemy")
        assert sa_models_res.status_code == 200
        sa_models = sa_models_res.json()
        assert all(m["orm_type"] == "SQLAlchemy" for m in sa_models)

        # 6. List Database Relationships (GET /database/relationships)
        rels_res = await client.get(f"/api/v1/projects/{project_id}/database/relationships")
        assert rels_res.status_code == 200
        rels_list = rels_res.json()
        assert len(rels_list) >= 2

        # Filter relationships by model
        cust_rels_res = await client.get(f"/api/v1/projects/{project_id}/database/relationships?model_name=Customer")
        assert cust_rels_res.status_code == 200
        cust_rels = cust_rels_res.json()
        assert len(cust_rels) >= 1
        assert any(r["source_model"] == "Customer" or r["target_model"] == "Customer" for r in cust_rels)

        # 7. Get ER Diagram (GET /database/diagram)
        diag_res = await client.get(f"/api/v1/projects/{project_id}/database/diagram")
        assert diag_res.status_code == 200
        diag_data = diag_res.json()
        assert "mermaid_code" in diag_data
        assert "erDiagram" in diag_data["mermaid_code"]
        assert diag_data["total_models"] >= 5
        assert diag_data["total_relationships"] >= 2
