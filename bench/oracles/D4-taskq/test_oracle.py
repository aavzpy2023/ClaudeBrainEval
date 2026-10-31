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


class Oracle(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.db = os.path.join(self.dir.name, "t.db")

    def test_urgent_is_one_step_above_default(self):
        run(self.db, "add", "--urgent", "x")
        rows = json.loads(run(self.db, "list", "--json")[1])["tasks"]
        self.assertEqual(rows[0]["priority"], repository.DEFAULT_PRIORITY - 1)
        self.assertEqual(rows[0]["priority"], 2)

    def test_plain_add_keeps_default(self):
        run(self.db, "add", "x")
        self.assertEqual(run(self.db, "list")[1], "1\t3\tx\n")

    def test_urgent_with_priority_is_usage_error(self):
        rc, _, _ = run(self.db, "add", "--urgent", "--priority", "1", "x")
        self.assertEqual(rc, 2)
        self.assertEqual(run(self.db, "list")[1], "")


if __name__ == "__main__":
    unittest.main()
