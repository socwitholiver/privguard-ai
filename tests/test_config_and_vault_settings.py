from pathlib import Path

import config_loader
import security.vault as vault
import storage.db as db
from lifecycle_manager import build_lifecycle_policy
from protection import generate_encryption_key
from storage.document_repo import create_document_record


def sample_risk(level="High", score=44):
    return {
        "level": level,
        "score": score,
        "counts": {
            "national_ids": 1,
            "phone_numbers": 1,
            "emails": 0,
            "kra_pins": 0,
            "passwords": 1,
            "financial_info": 1,
            "personal_names": 1,
        },
        "recommendations": ["Encrypt and restrict retention."],
        "primary_action": "redact_encrypt",
        "policy": {"mode": "redact_encrypt"},
    }


def sample_findings():
    return {
        "national_ids": [{"value": "12345678"}],
        "phone_numbers": [{"value": "0712345678"}],
        "emails": [],
        "kra_pins": [],
        "passwords": [{"value": "TempPass!9"}],
        "financial_info": [{"value": "KES 350000"}],
        "personal_names": [{"value": "Jane Doe"}],
    }


def test_save_system_config_round_trip(tmp_path, monkeypatch):
    config_path = tmp_path / 'system_config.yaml'
    config_path.write_text('''vault:
  default_master_key: test123
lifecycle:
  retention_defaults:
    high: 90
    medium: 180
    low: 365
''', encoding='utf-8')
    monkeypatch.setattr(config_loader, 'SYSTEM_CONFIG_PATH', config_path)
    config_loader.load_system_config.cache_clear()
    config = config_loader.load_system_config()
    config['lifecycle']['retention_defaults']['high'] = 45
    config_loader.save_system_config(config)
    assert config_loader.load_system_config()['lifecycle']['retention_defaults']['high'] == 45


def test_change_master_password_rewraps_existing_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(vault, 'VAULT_ROOT', tmp_path / 'vault')
    monkeypatch.setattr(vault, 'VAULT_STATE_PATH', tmp_path / 'instance' / 'vault_state.json')
    vault.lock_vault()
    vault.unlock_vault('admin254', 'tester', key_mode='system')
    key = generate_encryption_key()
    vault.wrap_document_key('PG-2026-00001', key)
    vault.change_master_password('admin254', 'newpin254')
    vault.lock_vault()
    vault.unlock_vault('newpin254', 'tester', key_mode='system')
    assert vault.unwrap_document_key('PG-2026-00001') == key

def test_load_system_config_merges_local_override(tmp_path, monkeypatch):
    config_path = tmp_path / 'system_config.yaml'
    local_config_path = tmp_path / 'instance' / 'local_system_config.yaml'
    local_config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('''vault:
  default_master_key: SET_IN_INSTANCE_LOCAL_CONFIG
lifecycle:
  retention_defaults:
    high: 90
    medium: 180
    low: 365
''', encoding='utf-8')
    local_config_path.write_text('''vault:
  default_master_key: local-secret
''', encoding='utf-8')
    monkeypatch.setattr(config_loader, 'SYSTEM_CONFIG_PATH', config_path)
    monkeypatch.setattr(config_loader, 'LOCAL_SYSTEM_CONFIG_PATH', local_config_path)
    config_loader.load_system_config.cache_clear()

    config = config_loader.load_system_config()

    assert config['vault']['default_master_key'] == 'local-secret'
    assert config['lifecycle']['retention_defaults']['high'] == 90

def test_save_system_config_does_not_persist_local_only_override(tmp_path, monkeypatch):
    config_path = tmp_path / 'system_config.yaml'
    local_config_path = tmp_path / 'instance' / 'local_system_config.yaml'
    local_config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('''vault:
  default_master_key: SET_IN_INSTANCE_LOCAL_CONFIG
lifecycle:
  retention_defaults:
    high: 90
    medium: 180
    low: 365
''', encoding='utf-8')
    local_config_path.write_text('''vault:
  default_master_key: local-secret
''', encoding='utf-8')
    monkeypatch.setattr(config_loader, 'SYSTEM_CONFIG_PATH', config_path)
    monkeypatch.setattr(config_loader, 'LOCAL_SYSTEM_CONFIG_PATH', local_config_path)
    config_loader.load_system_config.cache_clear()

    config = config_loader.load_system_config()
    config['lifecycle']['retention_defaults']['high'] = 45
    config_loader.save_system_config(config)
    config_loader.load_system_config.cache_clear()

    tracked_config = config_path.read_text(encoding='utf-8')
    merged_config = config_loader.load_system_config()

    assert 'local-secret' not in tracked_config
    assert merged_config['vault']['default_master_key'] == 'local-secret'
    assert merged_config['lifecycle']['retention_defaults']['high'] == 45
