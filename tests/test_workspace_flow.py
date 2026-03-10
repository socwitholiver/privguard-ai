import app as app_module
from app import app
from security.vault import lock_vault, unlock_vault, vault_is_unlocked


def test_dashboard_refresh_locks_user_access_but_keeps_background_vault_ready(tmp_path, monkeypatch):
    import security.vault as vault_module
    monkeypatch.setattr(vault_module, 'VAULT_ROOT', tmp_path / 'vault')
    monkeypatch.setattr(vault_module, 'VAULT_STATE_PATH', tmp_path / 'instance' / 'vault_state.json')
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
        assert vault_is_unlocked() is True


def test_launch_redirects_to_dashboard():
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            sess['display_name'] = 'Admin'
            sess['avatar_url'] = ''
            sess['theme'] = 'dark'
        response = client.get('/launch', follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/dashboard')


def test_watch_folder_enable_allows_system_automation_when_user_vault_access_is_locked(tmp_path, monkeypatch):
    incoming = tmp_path / 'incoming'
    incoming.mkdir()

    monkeypatch.setattr(app_module, '_validate_watch_folder', lambda _path: incoming)
    monkeypatch.setattr(app_module, 'configure_watch_folder', lambda folder_path, actor, reset_progress=False: {
        'enabled': True,
        'path': str(incoming),
        'configured_by': actor,
        'running': True,
        'mode': 'event',
    })
    monkeypatch.setattr(app_module, '_ensure_background_vault_access', lambda: True)
    started = {}
    monkeypatch.setattr(app_module, 'ensure_watch_folder_running', lambda processor, force_restart=False: started.setdefault('called', True))

    lock_vault()
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            sess['display_name'] = 'Admin'
            sess['avatar_url'] = ''
            sess['theme'] = 'dark'
            sess['vault_unlocked'] = False

        response = client.post('/api/watch-folder', json={'path': str(incoming), 'force_rescan': True})
        payload = response.get_json() or {}

    assert response.status_code == 200
    assert payload['enabled'] is True
    assert payload['path'] == str(incoming)
    assert started.get('called') is True


def test_workspace_api_does_not_auto_start_watch_runner(monkeypatch):
    started = {}
    monkeypatch.setattr(app_module, 'get_watch_folder_state', lambda: {'enabled': False, 'path': ''})
    monkeypatch.setattr(app_module, 'ensure_watch_folder_running', lambda *args, **kwargs: started.setdefault('called', True))

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            sess['display_name'] = 'Admin'
            sess['avatar_url'] = ''
            sess['theme'] = 'dark'
            sess['vault_unlocked'] = False
        response = client.get('/api/workspace')

    assert response.status_code == 200
    assert started == {}


def test_workspace_api_restarts_watch_runner_when_folder_is_enabled(monkeypatch):
    started = {}
    monkeypatch.setattr(app_module, 'get_watch_folder_state', lambda: {'enabled': True, 'path': 'C:/demo/WATCH FOLDER'})
    monkeypatch.setattr(app_module, '_ensure_background_vault_access', lambda: True)
    monkeypatch.setattr(app_module, 'ensure_watch_folder_running', lambda processor, force_restart=False: started.update({
        'called': True,
        'force_restart': force_restart,
        'processor': processor,
    }))

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            sess['display_name'] = 'Admin'
            sess['avatar_url'] = ''
            sess['theme'] = 'dark'
            sess['vault_unlocked'] = False
        response = client.get('/api/workspace')

    assert response.status_code == 200
    assert started['called'] is True
    assert started['force_restart'] is False
    assert started['processor'] is app_module._process_watch_file


def test_workspace_api_uses_uncapped_dashboard_metrics(monkeypatch):
    monkeypatch.setattr(app_module, 'get_watch_folder_state', lambda: {'enabled': False, 'path': ''})
    monkeypatch.setattr(app_module, 'summarize_scan_events', lambda limit=50: {
        'documents_scanned': 50,
        'risk_distribution': {'High': 50, 'Medium': 0, 'Low': 0},
        'average_risk_score': 82.5,
        'entity_totals': {},
        'trend_scores': [10, 20, 30],
    })
    monkeypatch.setattr(app_module, 'vault_summary', lambda: {
        'documents_total': 137,
        'protected_documents': 91,
        'high_risk_documents': 64,
        'pending_protection': 0,
        'review_required': 0,
        'archived_documents': 0,
        'deleted_documents': 0,
        'artifact_counts': {},
    })
    monkeypatch.setattr(app_module, 'list_documents', lambda limit=20: [])
    monkeypatch.setattr(app_module, 'list_recent_audit_events', lambda limit=12: [])
    monkeypatch.setattr(app_module, 'lifecycle_state', lambda: {})
    monkeypatch.setattr(app_module, '_system_settings_payload', lambda: {})

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            sess['display_name'] = 'Admin'
            sess['avatar_url'] = ''
            sess['theme'] = 'dark'
            sess['vault_unlocked'] = False
        response = client.get('/api/workspace')
        payload = response.get_json() or {}

    assert response.status_code == 200
    assert payload['summary']['documents_scanned'] == 137
    assert payload['summary']['protected_outputs'] == 91
    assert payload['summary']['high_risk_alerts'] == 64

def test_workspace_api_uses_uncapped_vault_lifecycle_metrics(monkeypatch):
    monkeypatch.setattr(app_module, 'get_watch_folder_state', lambda: {'enabled': False, 'path': ''})
    monkeypatch.setattr(app_module, 'summarize_scan_events', lambda limit=50: {
        'documents_scanned': 0,
        'risk_distribution': {'High': 0, 'Medium': 0, 'Low': 0},
        'average_risk_score': 0.0,
        'entity_totals': {},
        'trend_scores': [],
    })
    monkeypatch.setattr(app_module, 'vault_summary', lambda: {
        'documents_total': 500,
        'protected_documents': 480,
        'high_risk_documents': 475,
        'active_documents': 412,
        'expiring_documents': 21,
        'expired_documents': 9,
        'archived_documents': 38,
        'deleted_documents': 20,
        'pending_protection': 0,
        'review_required': 0,
        'artifact_counts': {},
    })
    monkeypatch.setattr(app_module, 'list_documents', lambda limit=20: [])
    monkeypatch.setattr(app_module, 'list_recent_audit_events', lambda limit=12: [])
    monkeypatch.setattr(app_module, 'lifecycle_state', lambda: {})
    monkeypatch.setattr(app_module, '_system_settings_payload', lambda: {})

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            sess['display_name'] = 'Admin'
            sess['avatar_url'] = ''
            sess['theme'] = 'dark'
            sess['vault_unlocked'] = False
        response = client.get('/api/workspace')
        payload = response.get_json() or {}

    assert response.status_code == 200
    assert payload['lifecycle_summary']['active'] == 412
    assert payload['lifecycle_summary']['expiring'] == 21
    assert payload['lifecycle_summary']['expired'] == 9
    assert payload['lifecycle_summary']['archived'] == 38
    assert payload['lifecycle_summary']['deleted'] == 20

def test_demo_reset_api_clears_workspace_and_stops_background_services(monkeypatch):
    events = {}

    monkeypatch.setattr(app_module, 'stop_watch_folder_runner', lambda: events.setdefault('watch_stopped', True))
    monkeypatch.setattr(app_module, 'stop_lifecycle_runner', lambda: events.setdefault('lifecycle_stopped', True))
    monkeypatch.setattr(app_module, 'clear_demo_workspace', lambda: {
        'watch_folder': 'C:/demo/WATCH FOLDER',
        'target_count': 0,
        'seeded_file_count': 0,
        'removed_watch_files': 500,
        'removed_vault_files': {'originals': 10, 'redacted': 10, 'encrypted': 10, 'reports': 10, 'keys': 10, 'logs': 1},
        'reset_database_rows': {'audit_events': 10, 'scan_events': 10, 'documents': 10, 'document_artifacts': 10},
        'removed_audit_archive_entries': 1,
        'watch_state_reset': True,
    })
    monkeypatch.setattr(app_module, 'disable_watch_folder', lambda actor=None: {
        'enabled': False,
        'path': 'C:/demo/WATCH FOLDER',
        'running': False,
        'mode': 'idle',
    })
    monkeypatch.setattr(app_module, '_workspace_payload', lambda: {
        'summary': {'documents_scanned': 0, 'protected_outputs': 0, 'high_risk_alerts': 0},
        'recent_files': [],
        'activity': [],
        'watch_folder': {'enabled': False, 'path': 'C:/demo/WATCH FOLDER'},
        'vault_summary': {'documents_total': 0},
        'lifecycle_summary': {},
        'lifecycle_engine': {},
        'settings': {},
        'user': {'username': 'admin'},
    })
    monkeypatch.setattr(app_module, 'log_audit_event', lambda **kwargs: events.update({'event_type': kwargs['event_type']}))

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            sess['display_name'] = 'Admin'
            sess['avatar_url'] = ''
            sess['theme'] = 'dark'
            sess['vault_unlocked'] = False
        response = client.post('/api/demo/reset')
        payload = response.get_json() or {}

    assert response.status_code == 200
    assert payload['demo']['seeded_file_count'] == 0
    assert payload['workspace']['summary']['documents_scanned'] == 0
    assert payload['watch_folder']['enabled'] is False
    assert events['watch_stopped'] is True
    assert events['lifecycle_stopped'] is True
    assert events['event_type'] == 'demo_workflow_reset'


def test_demo_rebuild_api_restarts_demo_workflow(monkeypatch):
    events = {}

    monkeypatch.setattr(app_module, '_ensure_background_vault_access', lambda: True)
    monkeypatch.setattr(app_module, 'stop_watch_folder_runner', lambda: events.setdefault('stopped', True))
    monkeypatch.setattr(app_module, 'rebuild_demo_workspace', lambda target_count: {
        'watch_folder': 'C:/demo/WATCH FOLDER',
        'target_count': target_count,
        'seeded_file_count': 500,
        'removed_watch_files': 500,
        'removed_vault_files': {'originals': 10, 'redacted': 10, 'encrypted': 10, 'reports': 10, 'keys': 10, 'logs': 1},
        'reset_database_rows': {'audit_events': 10, 'scan_events': 10, 'documents': 10, 'document_artifacts': 10},
        'removed_audit_archive_entries': 1,
        'watch_state_reset': True,
    })
    monkeypatch.setattr(app_module, 'configure_watch_folder', lambda folder_path, actor, reset_progress=False: {
        'enabled': True,
        'path': folder_path,
        'configured_by': actor,
        'running': True,
        'mode': 'event',
    })
    monkeypatch.setattr(app_module, 'ensure_watch_folder_running', lambda processor, force_restart=False: events.update({'started': True, 'force_restart': force_restart}))
    monkeypatch.setattr(app_module, 'log_audit_event', lambda **kwargs: events.update({'event_type': kwargs['event_type']}))

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            sess['display_name'] = 'Admin'
            sess['avatar_url'] = ''
            sess['theme'] = 'dark'
            sess['vault_unlocked'] = False
        response = client.post('/api/demo/rebuild')
        payload = response.get_json() or {}

    assert response.status_code == 200
    assert payload['demo']['seeded_file_count'] == 500
    assert payload['watch_folder']['path'] == 'C:/demo/WATCH FOLDER'
    assert events['stopped'] is True
    assert events['started'] is True
    assert events['force_restart'] is True
    assert events['event_type'] == 'demo_workflow_rebuilt'


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

def test_background_vault_access_requires_local_system_pin(monkeypatch):
    monkeypatch.setattr(app_module, 'vault_is_unlocked', lambda: False)
    monkeypatch.setattr(app_module, 'vault_is_configured', lambda: False)
    monkeypatch.setattr(app_module, 'vault_uses_system_master_key', lambda: False)
    monkeypatch.setattr(app_module, 'get_default_master_key', lambda: (_ for _ in ()).throw(ValueError('missing local pin')))
    started = {}
    monkeypatch.setattr(app_module, 'unlock_vault', lambda *args, **kwargs: started.setdefault('called', True))

    assert app_module._ensure_background_vault_access() is False
    assert started == {}


