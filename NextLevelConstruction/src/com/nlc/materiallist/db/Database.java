package com.nlc.materiallist.db;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;

/**
 * Opens (creating if needed) a single local SQLite file that holds every project.
 * By default it lives next to the app in the user's home folder so the data survives
 * across runs without asking the user anything:
 *   ~/NextLevelConstruction/material_list.db
 */
public final class Database {

    private static Connection connection;

    private Database() {}

    public static synchronized Connection get() {
        if (connection == null) {
            try {
                Class.forName("org.sqlite.JDBC");
                Path dir = Paths.get(System.getProperty("user.home"), "NextLevelConstruction");
                dir.toFile().mkdirs();
                Path dbFile = dir.resolve("material_list.db");
                connection = DriverManager.getConnection("jdbc:sqlite:" + dbFile.toAbsolutePath());
                try (Statement st = connection.createStatement()) {
                    st.execute("PRAGMA foreign_keys = ON;");
                }
                runSchema();
            } catch (Exception e) {
                throw new RuntimeException("Could not open local database", e);
            }
        }
        return connection;
    }

    private static void runSchema() throws IOException, SQLException {
        String sql = readSchemaSql();
        try (Statement st = connection.createStatement()) {
            for (String stmt : sql.split(";")) {
                String trimmed = stmt.trim();
                if (!trimmed.isEmpty()) st.execute(trimmed);
            }
        }
    }

    private static String readSchemaSql() throws IOException {
        // resources/schema.sql is on the classpath (added as a source folder in .classpath)
        try (InputStream in = Database.class.getClassLoader().getResourceAsStream("schema.sql")) {
            if (in == null) throw new IOException("schema.sql not found on classpath");
            StringBuilder sb = new StringBuilder();
            try (BufferedReader r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
                String line;
                while ((line = r.readLine()) != null) sb.append(line).append('\n');
            }
            return sb.toString();
        }
    }
}
