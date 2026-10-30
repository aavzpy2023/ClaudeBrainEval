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

    def test_dead_json_lists_only_dead_tasks(self):
        make_dead(self.db)
        run(self.db, "add", "fine")
        rc, out, _ = run(self.db, "dead", "--json")
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out), {"v": 1, "tasks": [{"id": 1, "text": "doomed"}]})

    def test_dead_json_empty(self):
        rc, out, _ = run(self.db, "dead", "--json")
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out), {"v": 1, "tasks": []})

    def test_plain_dead_unchanged(self):
        make_dead(self.db)
        self.assertEqual(run(self.db, "dead")[1], "1\tdoomed\n")
