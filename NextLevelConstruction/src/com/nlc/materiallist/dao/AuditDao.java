package com.nlc.materiallist.dao;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Types;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.nlc.materiallist.calc.CalcEngine.AuditChange;
import com.nlc.materiallist.db.Database;

public class AuditDao {

    /** A stored audit entry. */
    public static final class Entry {
        public long id;
        public String ts, action, itemKey;
        public Integer oldQty;
        public int newQty;
    }

    /** The web app keeps only the last 400 entries. */
    public static final int MAX_ENTRIES = 400;

    /** Newest entry first. */
    public List<Entry> findLog(String projectId) {
        String sql = "SELECT id, ts, action, item_key, old_qty, new_qty FROM audit_log WHERE project_id=? ORDER BY id DESC";
        List<Entry> out = new ArrayList<>();
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            ps.setString(1, projectId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    Entry e = new Entry();
                    e.id = rs.getLong(1); e.ts = rs.getString(2); e.action = rs.getString(3); e.itemKey = rs.getString(4);
                    int old = rs.getInt(5);
                    e.oldQty = rs.wasNull() ? null : old;
                    e.newQty = rs.getInt(6);
                    out.add(e);
                }
            }
        } catch (SQLException ex) { throw new RuntimeException(ex); }
        return out;
    }

    public Map<String, Integer> getSnapshot(String projectId) {
        Map<String, Integer> out = new LinkedHashMap<>();
        try (PreparedStatement ps = Database.get().prepareStatement("SELECT item_key, qty FROM audit_snapshot WHERE project_id=? ORDER BY rowid")) {
            ps.setString(1, projectId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) out.put(rs.getString(1), rs.getInt(2));
            }
        } catch (SQLException ex) { throw new RuntimeException(ex); }
        return out;
    }

    public int countLog(String projectId) {
        try (PreparedStatement ps = Database.get().prepareStatement("SELECT COUNT(*) FROM audit_log WHERE project_id=?")) {
            ps.setString(1, projectId);
            try (ResultSet rs = ps.executeQuery()) { return rs.next() ? rs.getInt(1) : 0; }
        } catch (SQLException ex) { throw new RuntimeException(ex); }
    }

    /**
     * In one transaction: stores the changes (the first change ends up on top, like the web app's list),
     * trims the log to MAX_ENTRIES and replaces the snapshot. `changes` may be empty (baseline only).
     */
    public void saveRun(String projectId, String ts, List<AuditChange> changes, Map<String, Integer> newSnapshot) {
        Connection c = Database.get();
        try {
            c.setAutoCommit(false);
            try {
                try (PreparedStatement ps = c.prepareStatement(
                        "INSERT INTO audit_log(project_id, ts, action, item_key, old_qty, new_qty) VALUES (?,?,?,?,?,?)")) {
                    for (int i = changes.size() - 1; i >= 0; i--) {   // reverse: the first change gets the highest id
                        AuditChange ch = changes.get(i);
                        ps.setString(1, projectId); ps.setString(2, ts); ps.setString(3, ch.action); ps.setString(4, ch.itemKey);
                        if (ch.oldQty == null) ps.setNull(5, Types.INTEGER); else ps.setInt(5, ch.oldQty);
                        ps.setInt(6, ch.newQty);
                        ps.executeUpdate();
                    }
                }
                try (PreparedStatement ps = c.prepareStatement(
                        "DELETE FROM audit_log WHERE project_id=? AND id NOT IN (SELECT id FROM audit_log WHERE project_id=? ORDER BY id DESC LIMIT ?)")) {
                    ps.setString(1, projectId); ps.setString(2, projectId); ps.setInt(3, MAX_ENTRIES);
                    ps.executeUpdate();
                }
                try (PreparedStatement ps = c.prepareStatement("DELETE FROM audit_snapshot WHERE project_id=?")) {
                    ps.setString(1, projectId);
                    ps.executeUpdate();
                }
                try (PreparedStatement ps = c.prepareStatement("INSERT INTO audit_snapshot(project_id, item_key, qty) VALUES (?,?,?)")) {
                    for (Map.Entry<String, Integer> e : newSnapshot.entrySet()) {
                        ps.setString(1, projectId); ps.setString(2, e.getKey()); ps.setInt(3, e.getValue());
                        ps.executeUpdate();
                    }
                }
                c.commit();
            } catch (SQLException ex) {
                c.rollback();
                throw ex;
            } finally {
                c.setAutoCommit(true);
            }
        } catch (SQLException ex) { throw new RuntimeException(ex); }
    }
}
