from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.project import Project
from backend.app.schemas.project import ProjectCreate, ProjectUpdate
from backend.app.core.exceptions import NotFoundException
from backend.app.core.logging import logger


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
            status="pending",
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
        db.delete(project)
        db.commit()
        logger.info(f"Project deleted with id={project_id}")
