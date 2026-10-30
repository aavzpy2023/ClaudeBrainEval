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

    def test_blank_text_is_a_usage_error(self):
        for text in ("", "   ", "\t\n"):
            rc, out, err = run(self.db, "add", text)
            self.assertEqual(rc, 2, text)
            self.assertEqual(out, "")
            self.assertTrue(err.strip())
        self.assertEqual(run(self.db, "list")[1], "")

    def test_normal_text_still_works(self):
        self.assertEqual(run(self.db, "add", " hi ")[0], 0)
        self.assertEqual(len(run(self.db, "list")[1].splitlines()), 1)
