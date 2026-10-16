package com.nlc.materiallist.dao;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import com.nlc.materiallist.db.Database;
import com.nlc.materiallist.model.Project;
import com.nlc.materiallist.model.ProjectInfo;

public class ProjectDao {

    public List<Project> findAll() {
        String sql = "SELECT id, abbr, name, created_at FROM projects ORDER BY created_at";
        List<Project> out = new ArrayList<>();
        try (PreparedStatement ps = Database.get().prepareStatement(sql);
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                out.add(new Project(rs.getString(1), rs.getString(2), rs.getString(3), rs.getString(4)));
            }
        } catch (SQLException e) { throw new RuntimeException(e); }
        return out;
    }

    /** Creates a new project (job) plus its default supplier rows (FACTORY / FIELD, 0% tax). */
    public Project create(String abbr, String name) {
        String id = "p" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        String createdAt = Instant.now().toString();
        String cleanAbbr = (abbr == null || abbr.isBlank()) ? "JOB" : abbr.trim().toUpperCase();
        if (cleanAbbr.length() > 5) cleanAbbr = cleanAbbr.substring(0, 5);
        String cleanName = (name == null || name.isBlank()) ? cleanAbbr : name.trim();

        Connection c = Database.get();
        try {
            c.setAutoCommit(false);
            try (PreparedStatement ps = c.prepareStatement(
                    "INSERT INTO projects(id, abbr, name, created_at) VALUES (?,?,?,?)")) {
                ps.setString(1, id); ps.setString(2, cleanAbbr); ps.setString(3, cleanName); ps.setString(4, createdAt);
                ps.executeUpdate();
            }
            try (PreparedStatement ps = c.prepareStatement(
                    "INSERT INTO project_info(project_id, name) VALUES (?,?)")) {
                ps.setString(1, id); ps.setString(2, cleanName);
                ps.executeUpdate();
            }
            try (PreparedStatement ps = c.prepareStatement(
                    "INSERT INTO suppliers(project_id, name, tax, delay_days) VALUES (?,?,0,0)")) {
                for (String supplyName : new String[]{"FACTORY", "FIELD"}) {
                    ps.setString(1, id); ps.setString(2, supplyName);
                    ps.executeUpdate();
                }
            }
            c.commit();
        } catch (SQLException e) {
            try { c.rollback(); } catch (SQLException ignored) {}
            throw new RuntimeException(e);
        } finally {
            try { c.setAutoCommit(true); } catch (SQLException ignored) {}
        }
        return new Project(id, cleanAbbr, cleanName, createdAt);
    }

    public void rename(String projectId, String abbr, String name) {
        String sql = "UPDATE projects SET abbr=?, name=? WHERE id=?";
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            ps.setString(1, abbr); ps.setString(2, name); ps.setString(3, projectId);
            ps.executeUpdate();
        } catch (SQLException e) { throw new RuntimeException(e); }
    }

    public void delete(String projectId) {
        try (PreparedStatement ps = Database.get().prepareStatement("DELETE FROM projects WHERE id=?")) {
            ps.setString(1, projectId);
            ps.executeUpdate(); // ON DELETE CASCADE removes info/suppliers/materials/items too
        } catch (SQLException e) { throw new RuntimeException(e); }
    }

    public ProjectInfo getInfo(String projectId) {
        String sql = "SELECT name, jobsite, builder, created_by, arch_date, struct_date, total_sf " +
                     "FROM project_info WHERE project_id=?";
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            ps.setString(1, projectId);
            try (ResultSet rs = ps.executeQuery()) {
                ProjectInfo info = new ProjectInfo();
                if (rs.next()) {
                    info.name = ns(rs.getString(1)); info.jobsite = ns(rs.getString(2));
                    info.builder = ns(rs.getString(3)); info.createdBy = ns(rs.getString(4));
                    info.archDate = ns(rs.getString(5)); info.structDate = ns(rs.getString(6));
                    info.totalSF = ns(rs.getString(7));
                }
                return info;
            }
        } catch (SQLException e) { throw new RuntimeException(e); }
    }

    public void saveInfo(String projectId, ProjectInfo info) {
        String sql = "UPDATE project_info SET name=?, jobsite=?, builder=?, created_by=?, arch_date=?, struct_date=?, total_sf=? WHERE project_id=?";
        try (PreparedStatement ps = Database.get().prepareStatement(sql)) {
            ps.setString(1, info.name); ps.setString(2, info.jobsite); ps.setString(3, info.builder);
            ps.setString(4, info.createdBy); ps.setString(5, info.archDate); ps.setString(6, info.structDate);
            ps.setString(7, info.totalSF); ps.setString(8, projectId);
            ps.executeUpdate();
        } catch (SQLException e) { throw new RuntimeException(e); }
    }

    private static String ns(String s) { return s == null ? "" : s; }
}
