import contextlib, io, json, os, tempfile, unittest
from unittest import mock

from taskq import cli, repository


def run(db, *argv):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.dict(os.environ, {"TASKQ_DB": db}), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = cli.main(list(argv))
        except SystemExit as e:
            rc = e.code
    return rc, out.getvalue(), err.getvalue()


def make_dead(db, text="doomed"):
    run(db, "add", text)
    for _ in range(repository.MAX_ATTEMPTS):
        run(db, "fail", "1")


class Oracle(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.db = os.path.join(self.dir.name, "t.db")

    def test_done_requires_a_running_task(self):
        run(self.db, "add", "a")
        rc, _, err = run(self.db, "done", "1")
        self.assertEqual(rc, 1)
        self.assertIn("not running: 1", err)

    def test_done_after_claim_then_not_twice(self):
        run(self.db, "add", "a")
        run(self.db, "claim")
        self.assertEqual(run(self.db, "done", "1")[0], 0)
        rc, _, err = run(self.db, "done", "1")
        self.assertEqual(rc, 1)
        self.assertIn("not running: 1", err)

    def test_done_on_dead_task_fails(self):
        make_dead(self.db)
        self.assertEqual(run(self.db, "done", "1")[0], 1)

    def test_repository_done_returns_false_when_not_running(self):
        repo = repository.Repository(self.db)
        task_id = repo.enqueue("a")
        self.assertFalse(repo.done(task_id))
        repo.claim()
        self.assertTrue(repo.done(task_id))
