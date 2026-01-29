"""Configuration loading utilities for CLI."""

import json
from pathlib import Path

from missing_file_check.config.models import TaskConfig


def load_config_from_file(file_path: str) -> TaskConfig:
    """Load task configuration from YAML or JSON file."""
    path = Path(file_path)

    if path.suffix in [".yaml", ".yml"]:
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    elif path.suffix == ".json":
        import json

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")

    return TaskConfig(**data)


def load_config_from_database(task_id: str) -> TaskConfig:
    """Load task configuration from database."""
    # TODO: Implement database loading
    raise NotImplementedError("Database loading not yet implemented")
