package com.nlc.materiallist.dao;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Types;
import java.util.ArrayList;
import java.util.List;

import com.nlc.materiallist.db.Database;
import com.nlc.materiallist.model.ReceivedEntry;

public class ReceivedDao {

    /** Newest delivery first (the web app adds new rows at the top). */
    public List<ReceivedEntry> findByProject(String projectId) {
        String sql = "SELECT id, group_name, location, supply, date, material, length, species, qty, ticket, invoice, payment " +
                     "FROM received_log WHERE project_id=? ORDER BY id DESC";
        List<ReceivedEntry> out = new ArrayList<>();
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            ps.setString(1, projectId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    ReceivedEntry r = new ReceivedEntry();
                    r.id = rs.getLong(1); r.projectId = projectId;
                    r.group = ns(rs.getString(2)); r.location = ns(rs.getString(3)); r.supply = ns(rs.getString(4));
                    r.date = ns(rs.getString(5)); r.material = ns(rs.getString(6)); r.length = ns(rs.getString(7));
                    r.species = ns(rs.getString(8));
                    double q = rs.getDouble(9);
                    r.qty = rs.wasNull() ? null : q;
                    r.ticket = ns(rs.getString(10)); r.invoice = ns(rs.getString(11)); r.payment = ns(rs.getString(12));
                    out.add(r);
                }
            }
        } catch (SQLException e) { throw new RuntimeException(e); }
        return out;
    }

    public ReceivedEntry insert(ReceivedEntry r) {
        String sql = "INSERT INTO received_log(project_id, group_name, location, supply, date, material, length, species, qty, ticket, invoice, payment) " +
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)";
        try (PreparedStatement ps = Database.get().prepareStatement(sql, PreparedStatement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, r.projectId);
            bindFields(ps, r, 2);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                if (keys.next()) r.id = keys.getLong(1);
            }
        } catch (SQLException e) { throw new RuntimeException(e); }
        return r;
    }

    public void update(ReceivedEntry r) {
        String sql = "UPDATE received_log SET group_name=?, location=?, supply=?, date=?, material=?, length=?, species=?, qty=?, ticket=?, invoice=?, payment=? WHERE id=?";
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            bindFields(ps, r, 1);
            ps.setLong(12, r.id);
            ps.executeUpdate();
        } catch (SQLException e) { throw new RuntimeException(e); }
    }

    public void delete(long id) {
        try (PreparedStatement ps = Database.get().prepareStatement("DELETE FROM received_log WHERE id=?")) {
            ps.setLong(1, id);
            ps.executeUpdate();
        } catch (SQLException e) { throw new RuntimeException(e); }
    }

    /** Binds the 11 data fields (group .. payment) starting at parameter index `from`. */
    private static void bindFields(PreparedStatement ps, ReceivedEntry r, int from) throws SQLException {
        int i = from;
        ps.setString(i++, r.group); ps.setString(i++, r.location); ps.setString(i++, r.supply);
        ps.setString(i++, r.date); ps.setString(i++, r.material); ps.setString(i++, r.length);
        ps.setString(i++, r.species);
        if (r.qty == null) ps.setNull(i++, Types.DOUBLE); else ps.setDouble(i++, r.qty);
        ps.setString(i++, r.ticket); ps.setString(i++, r.invoice); ps.setString(i++, r.payment);
    }

    private static String ns(String s) { return s == null ? "" : s; }
}
