package com.nlc.materiallist.dao;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Types;
import java.util.ArrayList;
import java.util.List;

import com.nlc.materiallist.db.Database;
import com.nlc.materiallist.model.TakeoffItem;

public class TakeoffItemDao {

    public List<TakeoffItem> findBySection(String projectId, String sectionId) {
        String sql = "SELECT id, group_name, purpose, page_detail, material, length, species, lf, sf, sp, ea, location, status " +
                     "FROM takeoff_items WHERE project_id=? AND section_id=? ORDER BY id";
        List<TakeoffItem> out = new ArrayList<>();
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            ps.setString(1, projectId); ps.setString(2, sectionId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) out.add(map(rs, projectId, sectionId));
            }
        } catch (SQLException e) { throw new RuntimeException(e); }
        return out;
    }

    /** All line items across every section of a project — used by the Dashboard to total everything up. */
    public List<TakeoffItem> findByProject(String projectId) {
        String sql = "SELECT id, section_id, group_name, purpose, page_detail, material, length, species, lf, sf, sp, ea, location, status " +
                     "FROM takeoff_items WHERE project_id=? ORDER BY section_id, id";
        List<TakeoffItem> out = new ArrayList<>();
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            ps.setString(1, projectId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    TakeoffItem t = new TakeoffItem();
                    t.id = rs.getLong(1); t.projectId = projectId; t.sectionId = rs.getString(2);
                    t.group = ns(rs.getString(3)); t.purpose = ns(rs.getString(4)); t.pageDetail = ns(rs.getString(5));
                    t.material = ns(rs.getString(6)); t.length = ns(rs.getString(7)); t.species = ns(rs.getString(8));
                    t.lf = getNullableDouble(rs, 9); t.sf = getNullableDouble(rs, 10);
                    t.sp = ns(rs.getString(11)); t.ea = getNullableDouble(rs, 12);
                    t.location = ns(rs.getString(13)); t.status = ns(rs.getString(14));
                    out.add(t);
                }
            }
        } catch (SQLException e) { throw new RuntimeException(e); }
        return out;
    }

    private TakeoffItem map(ResultSet rs, String projectId, String sectionId) throws SQLException {
        TakeoffItem t = new TakeoffItem();
        t.id = rs.getLong(1); t.projectId = projectId; t.sectionId = sectionId;
        t.group = ns(rs.getString(2)); t.purpose = ns(rs.getString(3)); t.pageDetail = ns(rs.getString(4));
        t.material = ns(rs.getString(5)); t.length = ns(rs.getString(6)); t.species = ns(rs.getString(7));
        t.lf = getNullableDouble(rs, 8); t.sf = getNullableDouble(rs, 9);
        t.sp = ns(rs.getString(10)); t.ea = getNullableDouble(rs, 11);
        t.location = ns(rs.getString(12)); t.status = ns(rs.getString(13));
        return t;
    }

    public TakeoffItem insert(TakeoffItem t) {
        String sql = "INSERT INTO takeoff_items(project_id, section_id, group_name, purpose, page_detail, material, length, species, lf, sf, sp, ea, location, status) " +
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)";
        try (PreparedStatement ps = Database.get().prepareStatement(sql, PreparedStatement.RETURN_GENERATED_KEYS)) {
            bind(ps, t);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                if (keys.next()) t.id = keys.getLong(1);
            }
        } catch (SQLException e) { throw new RuntimeException(e); }
        return t;
    }

    public void update(TakeoffItem t) {
        String sql = "UPDATE takeoff_items SET group_name=?, purpose=?, page_detail=?, material=?, length=?, species=?, lf=?, sf=?, sp=?, ea=?, location=?, status=? WHERE id=?";
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            ps.setString(1, t.group); ps.setString(2, t.purpose); ps.setString(3, t.pageDetail);
            ps.setString(4, t.material); ps.setString(5, t.length); ps.setString(6, t.species);
            setNullableDouble(ps, 7, t.lf); setNullableDouble(ps, 8, t.sf);
            ps.setString(9, t.sp); setNullableDouble(ps, 10, t.ea);
            ps.setString(11, t.location); ps.setString(12, t.status);
            ps.setLong(13, t.id);
            ps.executeUpdate();
        } catch (SQLException e) { throw new RuntimeException(e); }
    }

    public void delete(long id) {
        try (PreparedStatement ps = Database.get().prepareStatement("DELETE FROM takeoff_items WHERE id=?")) {
            ps.setLong(1, id);
            ps.executeUpdate();
        } catch (SQLException e) { throw new RuntimeException(e); }
    }

    private void bind(PreparedStatement ps, TakeoffItem t) throws SQLException {
        ps.setString(1, t.projectId); ps.setString(2, t.sectionId); ps.setString(3, t.group);
        ps.setString(4, t.purpose); ps.setString(5, t.pageDetail); ps.setString(6, t.material);
        ps.setString(7, t.length); ps.setString(8, t.species);
        setNullableDouble(ps, 9, t.lf); setNullableDouble(ps, 10, t.sf);
        ps.setString(11, t.sp); setNullableDouble(ps, 12, t.ea);
        ps.setString(13, t.location); ps.setString(14, t.status);
    }

    private static void setNullableDouble(PreparedStatement ps, int idx, Double v) throws SQLException {
        if (v == null) ps.setNull(idx, Types.DOUBLE); else ps.setDouble(idx, v);
    }
    private static Double getNullableDouble(ResultSet rs, int idx) throws SQLException {
        double v = rs.getDouble(idx);
        return rs.wasNull() ? null : v;
    }
    private static String ns(String s) { return s == null ? "" : s; }
}
