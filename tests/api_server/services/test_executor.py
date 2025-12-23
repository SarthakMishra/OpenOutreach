# tests/api_server/services/test_executor.py
from unittest.mock import MagicMock, patch

from api_server.db.models import Run
from api_server.services.executor import create_run, get_run, list_runs


class TestCreateRun:
    """Test create_run() function."""

    @patch("api_server.services.executor.get_session")
    def test_create_run_success(self, mock_get_session):
        """Test successful run creation."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        touchpoint_input = {
            "type": "profile_visit",
            "url": "https://www.linkedin.com/in/test/",
        }
        tags = {"test": "value"}

        run_id = create_run("test_account", touchpoint_input, tags)

        # Verify run_id is returned
        assert isinstance(run_id, str)
        assert len(run_id) == 36  # UUID string length

        # Verify Run was created with correct data
        mock_session.add.assert_called_once()
        added_run = mock_session.add.call_args[0][0]
        assert isinstance(added_run, Run)
        assert added_run.handle == "test_account"
        assert added_run.touchpoint_type == "profile_visit"
        assert added_run.status == "pending"
        assert added_run.tags == tags

        mock_session.commit.assert_called_once()

    @patch("api_server.services.executor.get_session")
    def test_create_run_without_tags(self, mock_get_session):
        """Test run creation without tags."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        touchpoint_input = {"type": "connect", "url": "https://www.linkedin.com/in/test/"}

        run_id = create_run("test_account", touchpoint_input)

        assert isinstance(run_id, str)
        added_run = mock_session.add.call_args[0][0]
        assert added_run.tags is None

    @patch("api_server.services.executor.get_session")
    def test_create_run_unknown_type(self, mock_get_session):
        """Test run creation with unknown type defaults to 'unknown'."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        touchpoint_input = {"url": "https://www.linkedin.com/in/test/"}

        run_id = create_run("test_account", touchpoint_input)

        assert isinstance(run_id, str)
        added_run = mock_session.add.call_args[0][0]
        assert added_run.touchpoint_type == "unknown"


class TestGetRun:
    """Test get_run() function."""

    @patch("api_server.services.executor.get_session")
    def test_get_run_success(self, mock_get_session):
        """Test successful run retrieval."""
        mock_run = MagicMock()
        mock_run.run_id = "test-run-id"
        mock_run.handle = "test_account"
        mock_run.status = "completed"

        mock_session = MagicMock()
        mock_session.get.return_value = mock_run
        mock_get_session.return_value = mock_session

        result = get_run("test-run-id")

        assert result == mock_run
        mock_session.get.assert_called_once_with(Run, "test-run-id")

    @patch("api_server.services.executor.get_session")
    def test_get_run_not_found(self, mock_get_session):
        """Test run retrieval when not found."""
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_get_session.return_value = mock_session

        result = get_run("nonexistent-run-id")

        assert result is None


class TestListRuns:
    """Test list_runs() function."""

    @patch("api_server.services.executor.get_session")
    def test_list_runs_all(self, mock_get_session):
        """Test listing all runs."""
        mock_runs = [MagicMock(), MagicMock()]
        mock_query = MagicMock()
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_runs
        mock_query.count.return_value = 2

        mock_session = MagicMock()
        mock_session.query.return_value = mock_query
        mock_get_session.return_value = mock_session

        runs, total = list_runs()

        assert runs == mock_runs
        assert total == 2
        mock_session.query.assert_called_once_with(Run)

    @patch("api_server.services.executor.get_session")
    def test_list_runs_filtered_by_handle(self, mock_get_session):
        """Test listing runs filtered by handle."""
        mock_runs = [MagicMock()]
        mock_filtered_query = MagicMock()
        mock_filtered_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_runs
        mock_filtered_query.count.return_value = 1
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_filtered_query

        mock_session = MagicMock()
        mock_session.query.return_value = mock_query
        mock_get_session.return_value = mock_session

        runs, total = list_runs(handle="test_account")

        assert runs == mock_runs
        assert total == 1
        mock_query.filter.assert_called_once()

    @patch("api_server.services.executor.get_session")
    def test_list_runs_filtered_by_status(self, mock_get_session):
        """Test listing runs filtered by status."""
        mock_runs = [MagicMock()]
        mock_filtered_query = MagicMock()
        mock_filtered_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_runs
        mock_filtered_query.count.return_value = 1
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_filtered_query

        mock_session = MagicMock()
        mock_session.query.return_value = mock_query
        mock_get_session.return_value = mock_session

        runs, total = list_runs(status="completed")

        assert runs == mock_runs
        assert total == 1
        mock_query.filter.assert_called_once()

    @patch("api_server.services.executor.get_session")
    def test_list_runs_empty_result(self, mock_get_session):
        """Test listing runs when none exist."""
        mock_query = MagicMock()
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_query.count.return_value = 0

        mock_session = MagicMock()
        mock_session.query.return_value = mock_query
        mock_get_session.return_value = mock_session

        runs, total = list_runs()

        assert runs == []
        assert total == 0

