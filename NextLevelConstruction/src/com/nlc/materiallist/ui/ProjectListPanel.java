package com.nlc.materiallist.ui;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Cursor;
import java.awt.Dimension;
import java.awt.Font;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Locale;
import java.util.function.Consumer;

import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.SwingConstants;
import javax.swing.border.EmptyBorder;

import com.nlc.materiallist.dao.ProjectDao;
import com.nlc.materiallist.model.Project;

/** Lista ("All Jobs"): one row per job with its badge, name and creation date. Clicking a row opens the job. */
public class ProjectListPanel extends JPanel {

    private static final Color INK = new Color(0x10, 0x23, 0x3B);
    private static final Color GRAY = new Color(0x5B, 0x6B, 0x7A);
    private static final Color ORANGE = new Color(0xE2, 0x60, 0x0C);
    private static final Color LINE = new Color(0xC7, 0xD2, 0xDB);
    private static final DateTimeFormatter DATE = DateTimeFormatter.ofPattern("MMM d, yyyy", Locale.US);

    private final int rowCount;

    public ProjectListPanel(Consumer<Project> onOpen) {
        setLayout(new BorderLayout(0, 12));
        setBackground(Color.WHITE);
        setBorder(new EmptyBorder(24, 24, 24, 24));

        JLabel heading = new JLabel("All Jobs");
        heading.setFont(heading.getFont().deriveFont(Font.BOLD, 22f));
        heading.setForeground(INK);
        add(heading, BorderLayout.NORTH);

        List<Project> projects = new ProjectDao().findAll();
        rowCount = projects.size();

        JPanel rows = new JPanel();
        rows.setLayout(new BoxLayout(rows, BoxLayout.Y_AXIS));
        rows.setBackground(Color.WHITE);
        if (projects.isEmpty()) {
            JLabel empty = new JLabel("Nenhum job ainda. Clique em Home para criar o primeiro.");
            empty.setForeground(GRAY);
            rows.add(empty);
        }
        for (Project p : projects) {
            rows.add(row(p, onOpen));
            rows.add(Box.createVerticalStrut(8));
        }
        JPanel wrap = new JPanel(new BorderLayout());
        wrap.setBackground(Color.WHITE);
        wrap.add(rows, BorderLayout.NORTH);
        JScrollPane scroll = new JScrollPane(wrap);
        scroll.setBorder(BorderFactory.createEmptyBorder());
        scroll.getVerticalScrollBar().setUnitIncrement(24);
        add(scroll, BorderLayout.CENTER);
    }

    /** Number of job rows shown (used by the tests). */
    public int getRowCount() { return rowCount; }

    /** "Oct 16, 2026" — the same style as the web app's fmtDate; a blank or odd value shows a dash or as is. */
    public static String formatCreated(String iso, ZoneId zone) {
        if (iso == null || iso.isEmpty()) return "—";
        try { return DATE.format(Instant.parse(iso).atZone(zone)); }
        catch (RuntimeException e) { return iso; }
    }

    private JPanel row(Project p, Consumer<Project> onOpen) {
        JPanel row = new JPanel(new BorderLayout(14, 0));
        row.setBackground(Color.WHITE);
        row.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(LINE), new EmptyBorder(10, 14, 10, 14)));
        row.setMaximumSize(new Dimension(Integer.MAX_VALUE, 64));
        row.setCursor(new Cursor(Cursor.HAND_CURSOR));

        JLabel badge = new JLabel(p.abbr, SwingConstants.CENTER);
        badge.setOpaque(true);
        badge.setBackground(INK);
        badge.setForeground(Color.WHITE);
        badge.setFont(badge.getFont().deriveFont(Font.BOLD, 13f));
        badge.setPreferredSize(new Dimension(64, 40));

        JLabel name = new JLabel(p.name);
        name.setFont(name.getFont().deriveFont(Font.BOLD, 14f));
        name.setForeground(INK);
        JLabel meta = new JLabel("Criado em " + formatCreated(p.createdAt, ZoneId.systemDefault()));
        meta.setFont(meta.getFont().deriveFont(Font.PLAIN, 11.5f));
        meta.setForeground(GRAY);
        JPanel text = new JPanel(new BorderLayout());
        text.setBackground(Color.WHITE);
        text.add(name, BorderLayout.NORTH);
        text.add(meta, BorderLayout.SOUTH);

        JLabel arrow = new JLabel("›");
        arrow.setFont(arrow.getFont().deriveFont(Font.BOLD, 22f));
        arrow.setForeground(ORANGE);

        row.add(badge, BorderLayout.WEST);
        row.add(text, BorderLayout.CENTER);
        row.add(arrow, BorderLayout.EAST);
        java.awt.event.MouseAdapter click = new java.awt.event.MouseAdapter() {
            @Override public void mouseClicked(java.awt.event.MouseEvent e) { onOpen.accept(p); }
        };
        for (java.awt.Component c : new java.awt.Component[]{row, badge, name, meta, arrow, text}) c.addMouseListener(click);
        return row;
    }
}
