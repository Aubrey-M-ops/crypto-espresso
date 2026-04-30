import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import tempfile, pathlib, shutil
from unittest.mock import patch, MagicMock

from wiki_sync import sync_files


def test_sync_files_copies_new_file():
    with tempfile.TemporaryDirectory() as src_tmp, \
         tempfile.TemporaryDirectory() as dst_tmp:
        src_dir = pathlib.Path(src_tmp)
        dst_projects = pathlib.Path(dst_tmp) / "projects"
        dst_projects.mkdir()

        (src_dir / "BTC.md").write_text("# BTC content")
        changed = sync_files(src_dir, pathlib.Path(dst_tmp))

        assert "BTC" in changed
        assert (dst_projects / "BTC.md").read_text() == "# BTC content"


def test_sync_files_skips_unchanged_file():
    with tempfile.TemporaryDirectory() as src_tmp, \
         tempfile.TemporaryDirectory() as dst_tmp:
        src_dir = pathlib.Path(src_tmp)
        dst_projects = pathlib.Path(dst_tmp) / "projects"
        dst_projects.mkdir()

        content = "# BTC content"
        (src_dir / "BTC.md").write_text(content)
        (dst_projects / "BTC.md").write_text(content)

        changed = sync_files(src_dir, pathlib.Path(dst_tmp))
        assert changed == []


def test_sync_files_detects_updated_content():
    with tempfile.TemporaryDirectory() as src_tmp, \
         tempfile.TemporaryDirectory() as dst_tmp:
        src_dir = pathlib.Path(src_tmp)
        dst_projects = pathlib.Path(dst_tmp) / "projects"
        dst_projects.mkdir()

        (src_dir / "BTC.md").write_text("# BTC new content")
        (dst_projects / "BTC.md").write_text("# BTC old content")

        changed = sync_files(src_dir, pathlib.Path(dst_tmp))
        assert "BTC" in changed


def test_sync_files_returns_empty_when_no_wiki_files():
    with tempfile.TemporaryDirectory() as src_tmp, \
         tempfile.TemporaryDirectory() as dst_tmp:
        changed = sync_files(pathlib.Path(src_tmp), pathlib.Path(dst_tmp))
        assert changed == []


from wiki_sync import ensure_clone


def test_ensure_clone_skips_if_already_cloned():
    with tempfile.TemporaryDirectory() as tmpdir:
        working_dir = pathlib.Path(tmpdir)
        (working_dir / ".git").mkdir()  # simulate existing clone

        with patch("subprocess.run") as mock_run:
            ensure_clone("/opt/crypto-wiki-private.git", working_dir)
            mock_run.assert_not_called()


def test_ensure_clone_runs_git_clone_if_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        working_dir = pathlib.Path(tmpdir) / "new-clone"  # does not exist

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            ensure_clone("/opt/crypto-wiki-private.git", working_dir)
            args = mock_run.call_args[0][0]
            assert args[0] == "git"
            assert "clone" in args


from wiki_sync import commit_and_push


def test_commit_and_push_returns_false_when_nothing_to_commit():
    with tempfile.TemporaryDirectory() as tmpdir:
        working_dir = pathlib.Path(tmpdir)

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            if "--cached" in cmd and "--quiet" in cmd:
                mock.returncode = 0  # nothing staged
            else:
                mock.returncode = 0
            return mock

        with patch("subprocess.run", side_effect=fake_run):
            result = commit_and_push(working_dir)
            assert result is False


def test_commit_and_push_returns_true_when_changes_exist():
    with tempfile.TemporaryDirectory() as tmpdir:
        working_dir = pathlib.Path(tmpdir)

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            if "--cached" in cmd and "--quiet" in cmd:
                mock.returncode = 1  # changes staged
            else:
                mock.returncode = 0
            return mock

        with patch("subprocess.run", side_effect=fake_run):
            result = commit_and_push(working_dir)
            assert result is True


from wiki_sync import send_notification


def test_send_notification_posts_to_telegram():
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_ADMIN_CHAT_ID": "123456",
        }):
            send_notification(["BTC", "ARB", "FET"])

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        body = call_kwargs["json"]
        assert body["chat_id"] == "123456"
        assert "BTC" in body["text"]
        assert "3" in body["text"]


def test_send_notification_skips_when_token_missing():
    with patch("httpx.post") as mock_post:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            send_notification(["BTC"])
        mock_post.assert_not_called()


import wiki_sync
from wiki_sync import main


def test_main_skips_when_no_wiki_files(tmp_path):
    with patch.object(wiki_sync, "WIKI_DIR", tmp_path), \
         patch.object(wiki_sync, "WORKING_DIR", tmp_path / "working"), \
         patch.object(wiki_sync, "BARE_REPO", "/opt/crypto-wiki-private.git"), \
         patch("wiki_sync.ensure_clone") as mock_clone, \
         patch("wiki_sync.send_notification") as mock_notify:
        main()
        mock_clone.assert_not_called()
        mock_notify.assert_not_called()


def test_main_calls_full_pipeline_when_files_exist(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "BTC.md").write_text("# BTC")

    with patch.object(wiki_sync, "WIKI_DIR", wiki_dir), \
         patch.object(wiki_sync, "WORKING_DIR", tmp_path / "working"), \
         patch.object(wiki_sync, "BARE_REPO", "/opt/crypto-wiki-private.git"), \
         patch("wiki_sync.ensure_clone") as mock_clone, \
         patch("wiki_sync.sync_files", return_value=["BTC"]) as mock_sync, \
         patch("wiki_sync.commit_and_push", return_value=True) as mock_push, \
         patch("wiki_sync.send_notification") as mock_notify:
        main()
        mock_clone.assert_called_once()
        mock_sync.assert_called_once()
        mock_push.assert_called_once()
        mock_notify.assert_called_once_with(["BTC"])


def test_main_skips_notification_when_nothing_committed(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "BTC.md").write_text("# BTC")

    with patch.object(wiki_sync, "WIKI_DIR", wiki_dir), \
         patch.object(wiki_sync, "WORKING_DIR", tmp_path / "working"), \
         patch.object(wiki_sync, "BARE_REPO", "/opt/crypto-wiki-private.git"), \
         patch("wiki_sync.ensure_clone"), \
         patch("wiki_sync.sync_files", return_value=["BTC"]), \
         patch("wiki_sync.commit_and_push", return_value=False), \
         patch("wiki_sync.send_notification") as mock_notify:
        main()
        mock_notify.assert_not_called()
