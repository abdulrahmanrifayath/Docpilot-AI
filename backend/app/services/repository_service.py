import os
import re
import shutil
import zipfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from fastapi import UploadFile
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.exceptions import ValidationException, NotFoundException
from backend.app.core.logging import logger
from backend.app.models.project import Project
from backend.app.schemas.project import FileItem, FileTreeResponse, ProjectStatus

GITHUB_URL_REGEX = re.compile(
    r"^https?://(www\.)?github\.com/[\w.-]+/[\w.-]+(\.git)?/?$"
)

EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".pyw": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".json": "JSON",
    ".md": "Markdown",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".toml": "TOML",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".cs": "C#",
    ".php": "PHP",
    ".sh": "Shell",
    ".dockerfile": "Dockerfile",
}


class RepositoryService:
    @staticmethod
    def get_repo_dir(project_id: str) -> Path:
        base_dir = Path(settings.REPO_STORAGE_PATH).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)
        return (base_dir / project_id).resolve()

    @staticmethod
    def validate_github_url(url: str) -> str:
        clean_url = url.strip()
        if not GITHUB_URL_REGEX.match(clean_url):
            raise ValidationException(
                "Invalid GitHub URL. Must be in format: https://github.com/owner/repository",
                details={"url": url},
            )
        return clean_url

    @classmethod
    def extract_zip_archive(
        cls, project: Project, file: UploadFile, db: Session
    ) -> Project:
        # Validate filename and extension
        if not file.filename or not file.filename.lower().endswith(".zip"):
            raise ValidationException("Only .zip archive files are accepted.")

        project.status = ProjectStatus.UPLOADING.value
        project.status_message = "Uploading and extracting ZIP archive..."
        db.commit()

        repo_dir = cls.get_repo_dir(project.id)

        # Clear existing repository directory
        if repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)
        repo_dir.mkdir(parents=True, exist_ok=True)

        temp_zip_path = repo_dir / "upload_temp.zip"
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        total_read = 0

        try:
            with open(temp_zip_path, "wb") as f_out:
                while chunk := file.file.read(1024 * 1024):  # 1MB chunks
                    total_read += len(chunk)
                    if total_read > max_bytes:
                        raise ValidationException(
                            f"Uploaded file exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
                        )
                    f_out.write(chunk)

            # Validate ZIP format
            if not zipfile.is_zipfile(temp_zip_path):
                raise ValidationException("The uploaded file is not a valid or readable ZIP archive.")

            extract_target_dir = repo_dir / "contents"
            extract_target_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(temp_zip_path, "r") as zf:
                for zip_info in zf.infolist():
                    raw_filename = zip_info.filename

                    # Skip empty entries
                    if not raw_filename:
                        continue

                    # Check for path traversal / Zip Slip
                    norm_path = os.path.normpath(raw_filename)
                    if norm_path.startswith("..") or os.path.isabs(norm_path):
                        raise ValidationException("Zip archive contains illegal path traversal components.")

                    target_file_path = (extract_target_dir / norm_path).resolve()
                    if not target_file_path.is_relative_to(extract_target_dir.resolve()):
                        raise ValidationException("Zip-slip vulnerability detected: illegal extraction target.")

                    # Check if any component is ignored
                    path_parts = set(Path(norm_path).parts)
                    if path_parts.intersection(set(settings.IGNORED_DIRECTORIES)):
                        continue
                    if Path(norm_path).name in settings.IGNORED_FILES:
                        continue

                    # If it's a directory, create it
                    if zip_info.is_dir():
                        target_file_path.mkdir(parents=True, exist_ok=True)
                        continue

                    # Ensure parent dir exists and extract file safely
                    target_file_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(zip_info) as source, open(target_file_path, "wb") as target:
                        shutil.copyfileobj(source, target)

            # Remove temporary zip file
            if temp_zip_path.exists():
                temp_zip_path.unlink()

            # If there is a single top-level folder inside contents, flatten it into repo_dir
            extracted_items = list(extract_target_dir.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                single_dir = extracted_items[0]
                for item in single_dir.iterdir():
                    shutil.move(str(item), str(repo_dir))
                shutil.rmtree(extract_target_dir, ignore_errors=True)
            else:
                for item in extracted_items:
                    shutil.move(str(item), str(repo_dir))
                shutil.rmtree(extract_target_dir, ignore_errors=True)

            project.repository_path = str(repo_dir)
            project.status = ProjectStatus.READY.value
            project.status_message = "ZIP archive extracted successfully."
            db.commit()
            db.refresh(project)
            logger.info(f"Successfully extracted ZIP archive for project {project.id} into {repo_dir}")
            return project

        except Exception as e:
            logger.error(f"Error extracting ZIP for project {project.id}: {e}")
            if repo_dir.exists():
                shutil.rmtree(repo_dir, ignore_errors=True)
            project.status = ProjectStatus.FAILED.value
            project.status_message = f"ZIP extraction failed: {str(e)}"
            db.commit()
            if isinstance(e, ValidationException):
                raise e
            raise ValidationException(f"Failed to process ZIP archive: {str(e)}")

    @classmethod
    def clone_github_repo(
        cls, project: Project, repo_url: str, db: Session
    ) -> Project:
        clean_url = cls.validate_github_url(repo_url)

        project.status = ProjectStatus.CLONING.value
        project.source_url = clean_url
        project.status_message = f"Cloning repository from {clean_url}..."
        db.commit()

        repo_dir = cls.get_repo_dir(project.id)

        # Clear existing repository directory
        if repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)
        repo_dir.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Starting git clone for project {project.id}: {clean_url}")
            cmd = [
                "git",
                "clone",
                "--depth",
                "1",
                "--single-branch",
                clean_url,
                str(repo_dir),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            if result.returncode != 0:
                err_msg = result.stderr.strip() or "Git clone exited with non-zero status"
                logger.error(f"Git clone failed for {clean_url}: {err_msg}")
                if repo_dir.exists():
                    shutil.rmtree(repo_dir, ignore_errors=True)
                project.status = ProjectStatus.FAILED.value
                project.status_message = f"Failed to clone repository: {err_msg}"
                db.commit()
                raise ValidationException(f"Failed to clone GitHub repository: {err_msg}")

            # Remove .git directory for security and storage hygiene
            git_folder = repo_dir / ".git"
            if git_folder.exists():
                # On Windows, files in .git may be read-only, handle onerror
                def handle_remove_readonly(func, path, exc):
                    import stat
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                shutil.rmtree(git_folder, onerror=handle_remove_readonly)

            project.repository_path = str(repo_dir)
            project.status = ProjectStatus.READY.value
            project.status_message = "Repository cloned successfully."
            db.commit()
            db.refresh(project)
            logger.info(f"Successfully cloned project {project.id} into {repo_dir}")
            return project

        except subprocess.TimeoutExpired:
            logger.error(f"Git clone timed out for project {project.id}: {clean_url}")
            if repo_dir.exists():
                shutil.rmtree(repo_dir, ignore_errors=True)
            project.status = ProjectStatus.FAILED.value
            project.status_message = "Git clone operation timed out after 120 seconds."
            db.commit()
            raise ValidationException("Git clone operation timed out. Please check the repository URL or size.")
        except Exception as e:
            if isinstance(e, ValidationException):
                raise e
            logger.error(f"Unexpected error during git clone for project {project.id}: {e}")
            if repo_dir.exists():
                shutil.rmtree(repo_dir, ignore_errors=True)
            project.status = ProjectStatus.FAILED.value
            project.status_message = f"Clone failed: {str(e)}"
            db.commit()
            raise ValidationException(f"Failed to clone repository: {str(e)}")

    @classmethod
    def get_project_file_tree(cls, project: Project) -> FileTreeResponse:
        if not project.repository_path or not os.path.exists(project.repository_path):
            if project.status == ProjectStatus.FAILED.value:
                raise ValidationException(f"Project repository is not available. Status: {project.status_message or 'FAILED'}")
            raise ValidationException("Project repository files have not been uploaded or cloned yet.")

        root_dir = Path(project.repository_path).resolve()
        ignored_dirs = set(settings.IGNORED_DIRECTORIES)
        ignored_files = set(settings.IGNORED_FILES)

        total_files = 0
        total_dirs = 0
        total_size = 0
        language_counts: Dict[str, int] = {}

        def build_tree(current_dir: Path, rel_prefix: str = "") -> List[FileItem]:
            nonlocal total_files, total_dirs, total_size
            items: List[FileItem] = []

            try:
                dir_entries = sorted(list(current_dir.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
            except (PermissionError, OSError) as err:
                logger.warning(f"Skipping inaccessible directory {current_dir}: {err}")
                return items

            for entry in dir_entries:
                name = entry.name
                if entry.is_dir():
                    if name in ignored_dirs:
                        continue
                    total_dirs += 1
                    child_rel = f"{rel_prefix}/{name}".lstrip("/")
                    children = build_tree(entry, child_rel)
                    dir_size = sum(c.size for c in children)
                    items.append(
                        FileItem(
                            name=name,
                            path=child_rel,
                            type="directory",
                            size=dir_size,
                            children=children,
                        )
                    )
                else:
                    if name in ignored_files:
                        continue
                    try:
                        file_stat = entry.stat()
                        f_size = file_stat.st_size
                    except OSError:
                        f_size = 0

                    total_files += 1
                    total_size += f_size
                    ext = entry.suffix.lower()
                    if ext in EXTENSION_LANGUAGE_MAP:
                        lang = EXTENSION_LANGUAGE_MAP[ext]
                        language_counts[lang] = language_counts.get(lang, 0) + 1

                    child_rel = f"{rel_prefix}/{name}".lstrip("/")
                    items.append(
                        FileItem(
                            name=name,
                            path=child_rel,
                            type="file",
                            size=f_size,
                            extension=ext or None,
                        )
                    )

            return items

        files = build_tree(root_dir)

        return FileTreeResponse(
            project_id=project.id,
            repository_path=str(root_dir),
            total_files=total_files,
            total_directories=total_dirs,
            total_size_bytes=total_size,
            files=files,
            language_counts=language_counts,
        )

    @classmethod
    def delete_project_storage(cls, project_id: str) -> None:
        repo_dir = cls.get_repo_dir(project_id)
        if repo_dir.exists():
            def handle_remove_readonly(func, path, exc):
                import stat
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception:
                    pass
            shutil.rmtree(repo_dir, onerror=handle_remove_readonly)
            logger.info(f"Deleted project storage for project {project_id} at {repo_dir}")
