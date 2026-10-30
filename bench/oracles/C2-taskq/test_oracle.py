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

    def test_count_empty(self):
        self.assertEqual(run(self.db, "count"), (0, "0\n", ""))

    def test_count_counts_every_status(self):
        for t in ("a", "b", "c"):
            run(self.db, "add", t)
        run(self.db, "claim")
        run(self.db, "done", "1")
        self.assertEqual(run(self.db, "count")[1], "3\n")
