package com.nlc.materiallist.ui;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.GridLayout;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.Consumer;

import javax.swing.BorderFactory;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.SwingConstants;

import com.nlc.materiallist.data.SeedData;
import com.nlc.materiallist.model.Project;

/**
 * Second-level circle screen shown after opening a project — one tile per screen,
 * in spreadsheet order: Dashboard, the 13 take-off sections (taken from
 * SeedData.SECTIONS, which is already in workbook order), Ordered (auto), Received, Audit Log,
 * then Materials DB and Suppliers & Tax.
 * SectionPanel is generic — it works for any sectionId in SeedData.SECTIONS.
 */
public class ProjectMenuPanel extends JPanel {

    public static final Map<String, String> TILES = new LinkedHashMap<>();
    private static final Map<String, String> ABBREVIATIONS = new LinkedHashMap<>();
    static {
        TILES.put("dashboard", "Dashboard");
        for (SeedData.Section s : SeedData.SECTIONS) TILES.put(s.id, s.label);
        TILES.put("ordered", "Ordered (auto)");
        TILES.put("received", "Received");
        TILES.put("audit", "Audit Log");
        TILES.put("database", "Materials DB");
        TILES.put("suppliers", "Suppliers & Tax");

        // Same circle labels as the web app (TAB_CIRCLES).
        ABBREVIATIONS.put("Dashboard", "DASH");
        ABBREVIATIONS.put("Sub-Floor", "SF");
        ABBREVIATIONS.put("1st Floor Walls", "1W");
        ABBREVIATIONS.put("2nd Floor Walls", "2W");
        ABBREVIATIONS.put("3rd Floor Walls", "3W");
        ABBREVIATIONS.put("4th Floor Walls", "4W");
        ABBREVIATIONS.put("5th Floor Walls", "5W");
        ABBREVIATIONS.put("6th Floor Walls", "6W");
        ABBREVIATIONS.put("Roof", "RF");
        ABBREVIATIONS.put("Flush Beam", "FB");
        ABBREVIATIONS.put("Shaft Wall", "SW");
        ABBREVIATIONS.put("Stair Tower", "ST");
        ABBREVIATIONS.put("Balcony", "BAL");
        ABBREVIATIONS.put("Windows & Doors", "WIN");
        ABBREVIATIONS.put("Ordered (auto)", "ORD");
        ABBREVIATIONS.put("Received", "RCV");
        ABBREVIATIONS.put("Audit Log", "AUD");
        ABBREVIATIONS.put("Materials DB", "DB");
        ABBREVIATIONS.put("Suppliers & Tax", "TAX");
    }

    public ProjectMenuPanel(Project project, Consumer<String> onOpenTile) {
        setLayout(new BorderLayout());
        setBackground(Color.WHITE);
        setBorder(BorderFactory.createEmptyBorder(24, 24, 24, 24));

        JLabel title = new JLabel(project.name);
        title.setFont(title.getFont().deriveFont(Font.BOLD, 15f));
        title.setForeground(new Color(0x5B, 0x6B, 0x7A));
        add(title, BorderLayout.NORTH);

        JPanel grid = new JPanel(new GridLayout(0, 3, 24, 24));
        grid.setBackground(Color.WHITE);
        grid.setBorder(BorderFactory.createEmptyBorder(20, 0, 0, 0));

        for (Map.Entry<String, String> tile : TILES.entrySet()) {
            grid.add(tileCell(tile.getValue(), () -> onOpenTile.accept(tile.getKey())));
        }

        JPanel gridWrap = new JPanel(new FlowLayout(FlowLayout.LEFT));
        gridWrap.setBackground(Color.WHITE);
        gridWrap.add(grid);
        JScrollPane scroll = new JScrollPane(gridWrap);
        scroll.setBorder(BorderFactory.createEmptyBorder());
        scroll.getVerticalScrollBar().setUnitIncrement(24);
        add(scroll, BorderLayout.CENTER);
    }

    private JPanel tileCell(String label, Runnable onClick) {
        JPanel cell = new JPanel(new BorderLayout(0, 8));
        cell.setBackground(Color.WHITE);
        CircleButton circle = new CircleButton(abbreviate(label));
        circle.addMouseListener(new java.awt.event.MouseAdapter() {
            @Override public void mouseClicked(java.awt.event.MouseEvent e) { onClick.run(); }
        });
        JLabel l = new JLabel(label, SwingConstants.CENTER);
        l.setFont(l.getFont().deriveFont(Font.BOLD, 11.5f));
        l.setForeground(new Color(0x10, 0x23, 0x3B));
        cell.add(circle, BorderLayout.CENTER);
        cell.add(l, BorderLayout.SOUTH);
        return cell;
    }

    private String abbreviate(String label) {
        String abbr = ABBREVIATIONS.get(label);
        if (abbr != null) return abbr;
        StringBuilder sb = new StringBuilder();
        for (String w : label.split(" ")) if (!w.isEmpty()) sb.append(Character.toUpperCase(w.charAt(0)));
        return sb.length() > 0 ? sb.toString() : label;
    }
}
