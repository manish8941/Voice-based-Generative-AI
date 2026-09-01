"""
Export Service Module
Writes generated markdown specifications into target repositories or project directories.
"""

import os
from pathlib import Path
from typing import Dict, List


class ExportService:
    """Handles saving generated blueprint files to local filesystem destinations."""

    @staticmethod
    def export_documents(documents: Dict[str, str], target_dir: str) -> List[str]:
        """Save a dictionary of {filename: content} into the target directory."""
        dest_path = Path(target_dir)
        dest_path.mkdir(parents=True, exist_ok=True)

        saved_files = []
        for filename, content in documents.items():
            if not content.strip():
                continue
            file_path = dest_path / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            saved_files.append(str(file_path))

        return saved_files

    @staticmethod
    def save_single_document(filename: str, content: str, target_dir: str) -> str:
        """Save a single document."""
        dest_path = Path(target_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        file_path = dest_path / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return str(file_path)
