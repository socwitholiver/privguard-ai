import app as app_module
from security.vault import unlock_vault

unlock_vault('admin254', 'debug', key_mode='system')
state_before = app_module.get_watch_folder_state()
print('BEFORE', state_before.get('enabled'), state_before.get('path'), state_before.get('last_processed_at'))
configured = app_module.configure_watch_folder(app_module._demo_watch_folder_path(), 'debug', reset_progress=True)
print('CONFIGURED', configured.get('enabled'), configured.get('path'))
running = app_module.ensure_watch_folder_running(app_module._process_watch_file, force_restart=True)
print('RUNNING', running.get('enabled'), running.get('running'), running.get('mode'), running.get('last_processed_at'), running.get('last_file'))
