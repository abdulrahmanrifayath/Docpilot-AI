from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.project import Project
from backend.app.schemas.project import ProjectCreate, ProjectUpdate, ProjectStatus
from backend.app.core.exceptions import NotFoundException
from backend.app.core.logging import logger
from backend.app.services.repository_service import RepositoryService


class ProjectService:
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
        return db.query(Project).order_by(Project.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_id(db: Session, project_id: str) -> Project:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise NotFoundException("Project", project_id)
        return project

    @staticmethod
    def create(db: Session, data: ProjectCreate) -> Project:
        project = Project(
            name=data.name,
            description=data.description,
            source_type=data.source_type,
            source_url=data.source_url,
            status=ProjectStatus.CREATED.value,
            status_message="Project created. Awaiting repository upload or clone.",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info(f"Project created with id={project.id}, name='{project.name}'")
        return project

    @staticmethod
    def update(db: Session, project_id: str, data: ProjectUpdate) -> Project:
        project = ProjectService.get_by_id(db, project_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)
        db.commit()
        db.refresh(project)
        logger.info(f"Project updated with id={project.id}")
        return project

    @staticmethod
    def delete(db: Session, project_id: str) -> None:
        project = ProjectService.get_by_id(db, project_id)
        # Delete repository files from disk
        RepositoryService.delete_project_storage(project_id)

        # Explicitly clean up related child tables
        from backend.app.models.code_entity import CodeEntity
        from backend.app.models.code_relationship import CodeRelationship
        from backend.app.models.api_endpoint import ApiEndpoint
        from backend.app.models.database_schema import DbModelRecord, DbRelationshipRecord
        from backend.app.models.knowledge_graph import KnowledgeNodeRecord, KnowledgeEdgeRecord
        from backend.app.models.documentation import DocumentationRecord

        db.query(DocumentationRecord).filter(DocumentationRecord.project_id == project_id).delete()
        db.query(KnowledgeEdgeRecord).filter(KnowledgeEdgeRecord.project_id == project_id).delete()
        db.query(KnowledgeNodeRecord).filter(KnowledgeNodeRecord.project_id == project_id).delete()
        db.query(DbRelationshipRecord).filter(DbRelationshipRecord.project_id == project_id).delete()
        db.query(DbModelRecord).filter(DbModelRecord.project_id == project_id).delete()
        db.query(ApiEndpoint).filter(ApiEndpoint.project_id == project_id).delete()
        db.query(CodeRelationship).filter(CodeRelationship.project_id == project_id).delete()
        db.query(CodeEntity).filter(CodeEntity.project_id == project_id).delete()

        db.delete(project)
        db.commit()
        logger.info(f"Project and associated storage deleted with id={project_id}")
