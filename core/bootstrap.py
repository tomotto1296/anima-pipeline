from core.config import migrate_legacy_settings_files
from core.history import configure_history


def prepare_bootstrap(base_dir: str, settings_dir: str, default_config: dict):
    configure_history(base_dir, settings_dir, default_config)
    migrate_legacy_settings_files(base_dir)
