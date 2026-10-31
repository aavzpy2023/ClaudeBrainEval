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
        run(self.db, "add", "first")
        run(self.db, "add", "--priority", "0", "second")

    def test_legacy_is_id_and_payload(self):
        self.assertEqual(run(self.db, "list", "--legacy")[1], "1\tfirst\n2\tsecond\n")

    def test_default_list_unchanged(self):
        self.assertEqual(run(self.db, "list")[1], "1\t5\tfirst\n2\t0\tsecond\n")


if __name__ == "__main__":
    unittest.main()
