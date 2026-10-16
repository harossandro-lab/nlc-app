package com.nlc.materiallist.dao;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

import com.nlc.materiallist.db.Database;
import com.nlc.materiallist.model.MaterialDbEntry;

public class MaterialDbDao {

    public List<MaterialDbEntry> findByProject(String projectId) {
        String sql = "SELECT id, material, length, species, supply, unit_price_out_tax " +
                     "FROM materials_db WHERE project_id=? ORDER BY id";
        List<MaterialDbEntry> out = new ArrayList<>();
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            ps.setString(1, projectId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    MaterialDbEntry d = new MaterialDbEntry();
                    d.id = rs.getLong(1); d.projectId = projectId;
                    d.material = rs.getString(2); d.length = rs.getString(3); d.species = rs.getString(4);
                    d.supply = rs.getString(5); d.unitPriceOutTax = rs.getDouble(6);
                    out.add(d);
                }
            }
        } catch (SQLException e) { throw new RuntimeException(e); }
        return out;
    }

    public MaterialDbEntry insert(MaterialDbEntry d) {
        String sql = "INSERT INTO materials_db(project_id, material, length, species, supply, unit_price_out_tax) VALUES (?,?,?,?,?,?)";
        try (PreparedStatement ps = Database.get().prepareStatement(sql, PreparedStatement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, d.projectId); ps.setString(2, d.material); ps.setString(3, d.length);
            ps.setString(4, d.species); ps.setString(5, d.supply); ps.setDouble(6, d.unitPriceOutTax);
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                if (keys.next()) d.id = keys.getLong(1);
            }
        } catch (SQLException e) { throw new RuntimeException(e); }
        return d;
    }

    public void update(MaterialDbEntry d) {
        String sql = "UPDATE materials_db SET material=?, length=?, species=?, supply=?, unit_price_out_tax=? WHERE id=?";
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            ps.setString(1, d.material); ps.setString(2, d.length); ps.setString(3, d.species);
            ps.setString(4, d.supply); ps.setDouble(5, d.unitPriceOutTax); ps.setLong(6, d.id);
            ps.executeUpdate();
        } catch (SQLException e) { throw new RuntimeException(e); }
    }

    public void delete(long id) {
        try (PreparedStatement ps = Database.get().prepareStatement("DELETE FROM materials_db WHERE id=?")) {
            ps.setLong(1, id);
            ps.executeUpdate();
        } catch (SQLException e) { throw new RuntimeException(e); }
    }
}
