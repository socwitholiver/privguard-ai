from app import app
from security.vault import lock_vault, unlock_vault, vault_is_unlocked


def test_dashboard_allows_first_entry_then_locks_on_refresh():
    lock_vault()
    unlock_vault('admin254', 'admin', key_mode='system')
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            sess['display_name'] = 'Admin'
            sess['avatar_url'] = ''
            sess['theme'] = 'dark'
            sess['vault_unlocked'] = True
            sess['allow_dashboard_once'] = True
        first = client.get('/dashboard')
        assert first.status_code == 200
        assert vault_is_unlocked() is True
        second = client.get('/dashboard')
        assert second.status_code == 200
        with client.session_transaction() as sess:
            assert sess.get('vault_unlocked') is False
        assert vault_is_unlocked() is False


def test_system_settings_api_returns_lifecycle_config():
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            sess['display_name'] = 'Admin'
            sess['avatar_url'] = ''
            sess['theme'] = 'dark'
            sess['vault_unlocked'] = False
        response = client.get('/api/system-settings')
        payload = response.get_json() or {}
        assert response.status_code == 200
        assert 'retention_defaults' in payload
        assert 'high' in payload['retention_defaults']
