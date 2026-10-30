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
        for t in ("a", "b", "c"):
            run(self.db, "add", t)

    def test_limit_plain(self):
        self.assertEqual(run(self.db, "list", "--limit", "2")[1], "1\t5\ta\n2\t5\tb\n")

    def test_limit_json(self):
        doc = json.loads(run(self.db, "list", "--json", "--limit", "1")[1])
        self.assertEqual(doc["tasks"], [{"id": 1, "priority": 5, "text": "a"}])

    def test_no_limit_lists_everything(self):
        self.assertEqual(len(run(self.db, "list")[1].splitlines()), 3)

    def test_limit_must_be_positive(self):
        self.assertEqual(run(self.db, "list", "--limit", "0")[0], 2)
