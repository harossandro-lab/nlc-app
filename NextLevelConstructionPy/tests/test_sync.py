import tempfile
import unittest
from pathlib import Path

from nlc import db
from nlc.dao import ProjectDao, SupplierDao, TakeoffItemDao
from nlc.models import TakeoffItem
from nlc.sync.engine import SyncEngine


class FakeRemote:
    """In-memory stand-in for the cloud: unique (table, uid), server-assigned seq."""
    def __init__(self):
        self.rows, self.seq, self.fail = {}, 0, False

    def push(self, changes):
        if self.fail:
            raise ConnectionError("offline")
        for c in changes:
            self.seq += 1
            self.rows[(c["table"], c["uid"])] = {**c, "seq": self.seq}

    def pull(self, since, limit):
        if self.fail:
            raise ConnectionError("offline")
        return sorted((dict(r) for r in self.rows.values() if r["seq"] > since), key=lambda r: r["seq"])[:limit]


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.remote = FakeRemote()
        self.a = db.connect(Path(self.tmp.name) / "a.db")
        self.b = db.connect(Path(self.tmp.name) / "b.db")
        self.ea, self.eb = SyncEngine(self.a, self.remote), SyncEngine(self.b, self.remote)
        self.addCleanup(self.b.close)
        self.addCleanup(self.a.close)

    def item(self, pid, material="2X4"):
        return TakeoffItemDao(self.a).insert(TakeoffItem(project_id=pid, section_id="roof", material=material, ea=3.0))

    def test_job_and_edit_reach_other_device(self):
        p = ProjectDao(self.a).create("AVN", "Avenel")
        it = self.item(p.id)
        self.ea.sync(); self.eb.sync()
        self.assertEqual([x.abbr for x in ProjectDao(self.b).find_all()], ["AVN"])
        rows = TakeoffItemDao(self.b).find_by_project(p.id)
        self.assertEqual((len(rows), rows[0].material, rows[0].ea), (1, "2X4", 3.0))
        it.material = "2X6"; TakeoffItemDao(self.a).update(it)
        self.ea.sync(); self.eb.sync()
        self.assertEqual(TakeoffItemDao(self.b).find_by_project(p.id)[0].material, "2X6")

    def test_delete_and_job_removal_propagate(self):
        p = ProjectDao(self.a).create("AVN", "Avenel")
        it = self.item(p.id)
        self.ea.sync(); self.eb.sync()
        TakeoffItemDao(self.a).delete(it.id)
        self.ea.sync(); self.eb.sync()
        self.assertEqual(TakeoffItemDao(self.b).find_by_project(p.id), [])
        ProjectDao(self.a).delete(p.id)
        self.ea.sync(); self.eb.sync()
        self.assertEqual(ProjectDao(self.b).find_all(), [])

    def test_offline_edits_queue_then_send(self):
        p = ProjectDao(self.a).create("AVN", "Avenel")
        self.remote.fail = True
        self.item(p.id)
        with self.assertRaises(ConnectionError):
            self.ea.sync()
        self.assertGreater(self.a.execute("SELECT COUNT(*) FROM sync_outbox").fetchone()[0], 0)
        self.remote.fail = False
        self.ea.sync(); self.eb.sync()
        self.assertEqual(len(TakeoffItemDao(self.b).find_by_project(p.id)), 1)
        self.assertEqual(self.b.execute("SELECT COUNT(*) FROM sync_outbox").fetchone()[0], 0)   # a pull never echoes back

    def test_last_writer_wins_and_pending_local_edit_survives_pull(self):
        p = ProjectDao(self.a).create("AVN", "Avenel")
        self.ea.sync(); self.eb.sync()
        sa = SupplierDao(self.a).find_by_project(p.id)[0]
        sb = [s for s in SupplierDao(self.b).find_by_project(p.id) if s.name == sa.name][0]
        sa.tax = 5; SupplierDao(self.a).update(sa)
        sb.tax = 7; SupplierDao(self.b).update(sb)
        self.ea.sync()          # A first
        self.eb.sync()          # B pushes after: B wins everywhere
        self.ea.sync()
        for conn in (self.a, self.b):
            self.assertEqual(conn.execute("SELECT tax FROM suppliers WHERE name=?", (sa.name,)).fetchone()[0], 7)

    def test_existing_data_is_backfilled_on_first_sync(self):
        p = ProjectDao(self.a).create("OLD", "Old job")
        self.a.execute("DELETE FROM sync_outbox"); self.a.commit()      # as if made before sync existed
        self.ea.sync(); self.eb.sync()
        self.assertEqual([x.abbr for x in ProjectDao(self.b).find_all()], ["OLD"])


if __name__ == "__main__":
    unittest.main()
