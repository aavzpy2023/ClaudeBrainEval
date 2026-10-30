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

    def test_requeue_makes_a_dead_task_claimable_again(self):
        make_dead(self.db)
        self.assertEqual(run(self.db, "requeue", "1")[0], 0)
        self.assertEqual(run(self.db, "dead")[1], "")
        rc, out, _ = run(self.db, "claim")
        self.assertEqual((rc, out), (0, "1\tdoomed\n"))

    def test_requeue_resets_attempts(self):
        make_dead(self.db)
        run(self.db, "requeue", "1")
        run(self.db, "claim")
        self.assertEqual(run(self.db, "fail", "1")[1], "pending\n")

    def test_requeue_refuses_tasks_that_are_not_dead(self):
        run(self.db, "add", "alive")
        rc, _, err = run(self.db, "requeue", "1")
        self.assertEqual(rc, 1)
        self.assertTrue(err.strip())
        self.assertEqual(run(self.db, "requeue", "99")[0], 1)
