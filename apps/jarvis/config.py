import os
from pathlib import Path
import yaml
from typing import Dict, Any

# Resolve the JARVIS root directory dynamically
JARVIS_ROOT = Path(__file__).resolve().parent.parent.parent

class JarvisConfig:
    """Central configuration manager for JARVIS."""
    def __init__(self):
        self.config_dir = JARVIS_ROOT / "config"
        self.config_paths = {
            "main": self.config_dir / "jarvis.yaml",
            "permissions": self.config_dir / "permissions.yaml",
            "models": self.config_dir / "models.yaml"
        }
        self.settings: Dict[str, Any] = {}
        self.load_all()

    def load_all(self):
        """Load all YAML configurations safely."""
        for name, path in self.config_paths.items():
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    self.settings[name] = yaml.safe_load(f) or {}
            else:
                self.settings[name] = {}

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self.settings.get(section, {}).get(key, default)

config = JarvisConfig()
