import json

import pytest

from scripts.ci import release_pr as controller


@pytest.fixture
def environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('GITHUB_REPOSITORY', 'owner/repo')
    monkeypatch.setenv('RELEASE_BOT_LOGIN', 'releaser[bot]')
    (tmp_path / 'VERSION').write_text('0.1.3\n')
    (tmp_path / 'uv.lock').write_text('version = 1\n')
    monkeypatch.setattr(controller.subprocess, 'check_output', lambda *args, **kwargs: 'dev-sha\n')
    monkeypatch.setattr(controller.subprocess, 'run', lambda *args, **kwargs: None)
    monkeypatch.setattr(controller, 'version_commit', lambda: 'release-sha')
    monkeypatch.setattr(controller, 'check_pr', lambda *args: True)
    monkeypatch.setattr(controller, 'record_for', lambda value: {'draft': False, 'tag_name': 'testpypi-v0.1.3', 'body': json.dumps({'version': '0.1.3', 'commit': 'release-sha'})})
    return tmp_path


def test_pending_publication_never_opens_a_patch_pr(environment, monkeypatch):
    monkeypatch.setattr(controller, 'record_for', lambda value: {'draft': True})
    monkeypatch.setattr(controller, 'pages', lambda path: [])
    calls = []
    def api(path, method='GET', data=None):
        calls.append(method)
        return {'object': {'sha': 'dev-sha'}}
    monkeypatch.setattr(controller, 'api', api)
    controller.main()
    assert calls == ['GET']


def test_release_commit_does_not_trigger_another_bump(environment, monkeypatch):
    monkeypatch.setattr(controller, 'version_commit', lambda: 'dev-sha')
    monkeypatch.setattr(controller, 'record_for', lambda value: {'draft': False, 'tag_name': 'testpypi-v0.1.3', 'body': json.dumps({'version': '0.1.3', 'commit': 'dev-sha'})})
    monkeypatch.setattr(controller, 'pages', lambda path: [])
    monkeypatch.setattr(controller, 'api', lambda path: {'object': {'sha': 'dev-sha'}})
    controller.main()
    assert (environment / 'VERSION').read_text() == '0.1.3\n'


def test_bot_commits_version_change_in_a_pr_not_to_dev(environment, monkeypatch):
    monkeypatch.setattr(controller, 'pages', lambda path: [])
    calls = []
    def api(path, method='GET', data=None):
        calls.append((path, method, data))
        if path.endswith('git/ref/heads/dev'):
            return {'object': {'sha': 'dev-sha'}}
        if path.endswith('git/commits/dev-sha'):
            return {'tree': {'sha': 'tree-sha'}}
        if 'matching-refs' in path:
            return []
        return {'sha': 'new-sha'}
    monkeypatch.setattr(controller, 'api', api)
    controller.main()
    tree = next(data for path, method, data in calls if path.endswith('git/trees'))
    assert tree['tree'][0]['content'] == '0.1.4\n'
    ref = next(data for path, method, data in calls if path.endswith('git/refs'))
    assert ref['ref'] == 'refs/heads/chore/release-version'
    pr = next(data for path, method, data in calls if path.endswith('/pulls'))
    assert pr['base'] == 'dev'
    assert not any(method != 'GET' and path.endswith('/heads/dev') for path, method, data in calls)


def test_automerge_requires_checks_on_current_head_and_current_dev(environment, monkeypatch):
    pr = {'head': {'sha': 'pr-sha'}}
    def api(path):
        if 'git/commits' in path:
            return {'parents': [{'sha': 'old-dev'}]}
        raise AssertionError('Must not query checks for stale base')
    monkeypatch.setattr(controller, 'api', api)
    assert not controller.ready_to_merge(pr, 'dev-sha')
    def checked_api(path):
        if 'git/commits' in path:
            return {'parents': [{'sha': 'dev-sha'}]}
        return {'check_runs': [
            {'id': 1, 'name': 'compatibility', 'app': {'slug': 'github-actions'}, 'conclusion': 'success'},
            {'id': 2, 'name': 'compatibility', 'app': {'slug': 'github-actions'}, 'conclusion': 'failure'},
        ]}
    monkeypatch.setattr(controller, 'api', checked_api)
    assert not controller.ready_to_merge(pr, 'dev-sha')
