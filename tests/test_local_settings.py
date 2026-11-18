"""Private configuration setup: fake values only, no API requests."""
import os
from unittest.mock import patch
from local_settings import load_local_settings
from scripts import configure_ai


def test_reader_loads_only_allowed_settings_and_never_runs_shell(tmp_path):
    path = tmp_path / '.env'
    path.write_text('# comment\nOPENAI_API_KEY="fake-test-key"\nOPENAI_MODEL=gpt-4o-mini\nHOME=changed\nBAD_LINE\n')
    with patch.dict(os.environ, {'HOME':'unchanged'}, clear=True):
        load_local_settings(path)
        assert os.environ['OPENAI_API_KEY']=='fake-test-key'
        assert os.environ['OPENAI_MODEL']=='gpt-4o-mini'
        assert os.environ['HOME']=='unchanged'


def test_existing_environment_wins(tmp_path):
    path=tmp_path / '.env'; path.write_text('OPENAI_API_KEY=file-value\n')
    with patch.dict(os.environ, {'OPENAI_API_KEY':'environment-value'}, clear=True):
        load_local_settings(path)
        assert os.environ['OPENAI_API_KEY']=='environment-value'


def test_missing_file_is_optional(tmp_path):
    with patch.dict(os.environ, {}, clear=True):
        load_local_settings(tmp_path / 'missing.env')
        assert 'OPENAI_API_KEY' not in os.environ


def test_setup_saves_with_private_permissions_and_hides_key(tmp_path, capsys):
    path=tmp_path / '.env'
    with patch.object(configure_ai,'SETTINGS_PATH',path),patch('getpass.getpass',return_value='fake-test-key'):
        configure_ai.main()
    assert path.stat().st_mode & 0o777 == 0o600
    assert 'OPENAI_API_KEY=fake-test-key' in path.read_text()
    assert 'fake-test-key' not in capsys.readouterr().out


def test_setup_preserves_existing_file(tmp_path):
    path=tmp_path / '.env'; path.write_text('preserve-me')
    with patch.object(configure_ai,'SETTINGS_PATH',path),patch('getpass.getpass') as prompt:
        configure_ai.main()
    assert path.read_text()=='preserve-me'
    prompt.assert_not_called()


def test_setup_empty_key_creates_no_file(tmp_path):
    path=tmp_path / '.env'
    with patch.object(configure_ai,'SETTINGS_PATH',path),patch('getpass.getpass',return_value=''):
        configure_ai.main()
    assert not path.exists()


def test_gemini_setup_preserves_other_provider_key(tmp_path, capsys):
    path=tmp_path / '.env';path.write_text('OPENAI_API_KEY=keep-this-key\nAI_PROVIDER=openai\n')
    with patch.object(configure_ai,'SETTINGS_PATH',path),patch('getpass.getpass',return_value='fake-google-key'):
        configure_ai.main(provider='gemini')
    content=path.read_text()
    assert 'OPENAI_API_KEY=keep-this-key' in content
    assert 'GEMINI_API_KEY=fake-google-key' in content
    assert 'AI_PROVIDER=gemini' in content
    assert path.stat().st_mode & 0o777 == 0o600
    assert 'fake-google-key' not in capsys.readouterr().out
