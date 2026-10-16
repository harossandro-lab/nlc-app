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
import javax.swing.SwingConstants;

import com.nlc.materiallist.model.Project;

/**
 * Second-level circle screen shown after opening a project — one tile per screen,
 * in spreadsheet order. This starter wires up Dashboard + Sub-Floor (the requested
 * example section) plus Materials DB / Suppliers, which the calculations need.
 * Add more tiles here the same way to bring in the other 12 take-off sections later
 * (SectionPanel is generic — it already works for any sectionId in SeedData.SECTIONS).
 */
public class ProjectMenuPanel extends JPanel {

    public static final Map<String, String> TILES = new LinkedHashMap<>();
    static {
        TILES.put("dashboard", "Dashboard");
        TILES.put("sub-floor", "Sub-Floor");
        TILES.put("database", "Materials DB");
        TILES.put("suppliers", "Suppliers & Tax");
        // To add e.g. 1st-Walls later:
        //   TILES.put("1st-walls", "1st Floor Walls");
        // SectionPanel already understands any sectionId present in SeedData.SECTIONS.
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
        add(gridWrap, BorderLayout.CENTER);
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
        switch (label) {
            case "Dashboard": return "DASH";
            case "Sub-Floor": return "SF";
            case "Materials DB": return "DB";
            case "Suppliers & Tax": return "TAX";
            default:
                String[] words = label.split(" ");
                StringBuilder sb = new StringBuilder();
                for (String w : words) if (!w.isEmpty()) sb.append(Character.toUpperCase(w.charAt(0)));
                return sb.length() > 0 ? sb.toString() : label;
        }
    }
}
