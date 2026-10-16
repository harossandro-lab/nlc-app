package com.nlc.materiallist.dao;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

import com.nlc.materiallist.db.Database;
import com.nlc.materiallist.model.Supplier;

public class SupplierDao {

    public List<Supplier> findByProject(String projectId) {
        String sql = "SELECT id, name, tax, delay_days FROM suppliers WHERE project_id=? ORDER BY id";
        List<Supplier> out = new ArrayList<>();
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            ps.setString(1, projectId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    Supplier s = new Supplier();
                    s.id = rs.getLong(1); s.projectId = projectId;
                    s.name = rs.getString(2); s.tax = rs.getDouble(3); s.delay = rs.getInt(4);
                    out.add(s);
                }
            }
        } catch (SQLException e) { throw new RuntimeException(e); }
        return out;
    }

    public Supplier insert(String projectId, String name, double tax, int delay) {
        String sql = "INSERT INTO suppliers(project_id, name, tax, delay_days) VALUES (?,?,?,?)";
        try (PreparedStatement ps = Database.get().prepareStatement(sql, PreparedStatement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, projectId); ps.setString(2, name); ps.setDouble(3, tax); ps.setInt(4, delay);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                Supplier s = new Supplier();
                s.projectId = projectId; s.name = name; s.tax = tax; s.delay = delay;
                if (keys.next()) s.id = keys.getLong(1);
                return s;
            }
        } catch (SQLException e) { throw new RuntimeException(e); }
    }

    public void update(Supplier s) {
        String sql = "UPDATE suppliers SET name=?, tax=?, delay_days=? WHERE id=?";
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            ps.setString(1, s.name); ps.setDouble(2, s.tax); ps.setInt(3, s.delay); ps.setLong(4, s.id);
            ps.executeUpdate();
        } catch (SQLException e) { throw new RuntimeException(e); }
    }

    public void delete(long id) {
        try (PreparedStatement ps = Database.get().prepareStatement("DELETE FROM suppliers WHERE id=?")) {
            ps.setLong(1, id);
            ps.executeUpdate();
        } catch (SQLException e) { throw new RuntimeException(e); }
    }
}
