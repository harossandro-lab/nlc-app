package com.nlc.materiallist.ui;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.Font;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import javax.swing.BorderFactory;
import javax.swing.JButton;
import javax.swing.JFileChooser;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.SwingConstants;
import javax.swing.border.EmptyBorder;
import javax.swing.table.AbstractTableModel;
import javax.swing.table.DefaultTableCellRenderer;

import com.nlc.materiallist.calc.CalcEngine;
import com.nlc.materiallist.calc.CalcEngine.OrderedLine;
import com.nlc.materiallist.calc.SectionOrder;
import com.nlc.materiallist.dao.MaterialDbDao;
import com.nlc.materiallist.dao.SupplierDao;
import com.nlc.materiallist.dao.TakeoffItemDao;
import com.nlc.materiallist.data.SeedData;
import com.nlc.materiallist.model.MaterialDbEntry;
import com.nlc.materiallist.model.Project;
import com.nlc.materiallist.model.Supplier;
import com.nlc.materiallist.model.TakeoffItem;

/**
 * Ordered (auto): the sum of QTY by GROUP -> ItemKey across every take-off section. It replaces the manual
 * TAKEOFF sheet and the Update_ORDERED_All macro of the workbook. Read-only; it is rebuilt each time it is opened.
 */
public class OrderedPanel extends JPanel {

    private static final Color INK = new Color(0x10, 0x23, 0x3B);
    private static final Color GRAY = new Color(0x5B, 0x6B, 0x7A);
    private static final Color ORANGE = new Color(0xE2, 0x60, 0x0C);
    private static final Color LINE = new Color(0xC7, 0xD2, 0xDB);

    private static final String[] COLUMNS = {"Group", "Material · Length · Species", "Qty", "Supply", "Unit $", "Total"};

    private enum Kind { GROUP, ITEM, SUBTOTAL, GRAND }

    private static final class Row {
        final Kind kind;
        final Object[] cells;
        Row(Kind kind, Object... cells) { this.kind = kind; this.cells = cells; }
    }

    private final List<Row> rows = new ArrayList<>();
    private final Map<String, Map<String, OrderedLine>> byGroup;
    private final String projectName;

    public OrderedPanel(Project project) {
        this.projectName = project.name;
        setLayout(new BorderLayout(0, 14));
        setBackground(Color.WHITE);
        setBorder(new EmptyBorder(22, 26, 26, 26));

        byGroup = CalcEngine.aggregateByGroup(
                SectionOrder.sort(new TakeoffItemDao().findByProject(project.id)),
                new MaterialDbDao().findByProject(project.id),
                new SupplierDao().findByProject(project.id));
        buildRows();

        JLabel heading = new JLabel("Ordered (auto)");
        heading.setFont(heading.getFont().deriveFont(Font.BOLD, 22f));
        heading.setForeground(INK);
        JLabel sub = new JLabel("Somado automaticamente de todas as seções, por GROUP → ItemKey — substitui o passo manual do TAKEOFF original.");
        sub.setFont(sub.getFont().deriveFont(Font.PLAIN, 12f));
        sub.setForeground(GRAY);
        JPanel titles = new JPanel(new BorderLayout(0, 4));
        titles.setBackground(Color.WHITE);
        titles.add(heading, BorderLayout.NORTH);
        titles.add(sub, BorderLayout.SOUTH);

        JButton export = new JButton("Export CSV");
        export.addActionListener(e -> exportCsv());
        JPanel top = new JPanel(new BorderLayout());
        top.setBackground(Color.WHITE);
        top.add(titles, BorderLayout.CENTER);
        top.add(export, BorderLayout.EAST);
        add(top, BorderLayout.NORTH);

        JTable table = new JTable(new Model());
        table.setRowHeight(24);
        table.setShowGrid(false);
        table.setIntercellSpacing(new java.awt.Dimension(0, 0));
        table.setFillsViewportHeight(true);
        table.getTableHeader().setReorderingAllowed(false);
        table.setDefaultRenderer(Object.class, new RowRenderer());
        int[] widths = {300, 300, 70, 100, 90, 110};
        for (int i = 0; i < widths.length; i++) table.getColumnModel().getColumn(i).setPreferredWidth(widths[i]);
        JScrollPane scroll = new JScrollPane(table);
        scroll.setBorder(BorderFactory.createLineBorder(LINE));
        add(scroll, BorderLayout.CENTER);
    }

    private void buildRows() {
        double grandTotal = 0;
        for (String g : CalcEngine.groupDisplayOrder(byGroup.keySet(), SeedData.GROUPS)) {
            Map<String, OrderedLine> entries = byGroup.get(g);
            rows.add(new Row(Kind.GROUP, g + "  (" + entries.size() + (entries.size() == 1 ? " item)" : " items)"), "", "", "", "", ""));
            double groupTotal = 0;
            for (OrderedLine e : entries.values()) {
                Double total = e.total();
                if (total != null) { groupTotal += total; grandTotal += total; }
                rows.add(new Row(Kind.ITEM, "", describe(e), e.qty, e.supply == null ? "—" : e.supply,
                        e.unit == null ? "—" : CalcEngine.fixed2(e.unit),
                        total == null ? "—" : money(total)));
            }
            rows.add(new Row(Kind.SUBTOTAL, "Subtotal — " + g, "", "", "", "", money(groupTotal)));
        }
        if (!rows.isEmpty()) rows.add(new Row(Kind.GRAND, "GRAND TOTAL", "", "", "", "", money(grandTotal)));
    }

    private static String describe(OrderedLine e) {
        StringBuilder sb = new StringBuilder();
        for (String part : new String[]{e.material, e.length, e.species}) {
            if (part == null || part.isEmpty()) continue;
            if (sb.length() > 0) sb.append(" · ");
            sb.append(part);
        }
        return sb.toString();
    }

    private static String money(double n) { return CalcEngine.money(n); }

    /** CSV exactly as the web app exports it: groups in first-seen order, header Group..Total. */
    public static String buildCsv(Map<String, Map<String, OrderedLine>> byGroup) {
        StringBuilder sb = new StringBuilder("Group,Material,Length,Species,Qty,Supply,Unit Price,Total\n");
        for (Map.Entry<String, Map<String, OrderedLine>> g : byGroup.entrySet()) {
            for (OrderedLine e : g.getValue().values()) {
                Double total = e.total();
                String[] cells = {g.getKey(), e.material, e.length, e.species, String.valueOf(e.qty),
                        e.supply == null ? "" : e.supply,
                        e.unit == null ? "" : CalcEngine.fixed2(e.unit),
                        total == null ? "" : CalcEngine.fixed2(total)};
                for (int i = 0; i < cells.length; i++) {
                    if (i > 0) sb.append(',');
                    sb.append(csvCell(cells[i]));
                }
                sb.append('\n');
            }
        }
        return sb.toString();
    }

    private static String csvCell(String v) {
        if (v == null) return "";
        if (v.contains(",") || v.contains("\"") || v.contains("\n")) return "\"" + v.replace("\"", "\"\"") + "\"";
        return v;
    }

    private void exportCsv() {
        JFileChooser chooser = new JFileChooser();
        String base = (projectName == null || projectName.isEmpty() ? "project" : projectName) + "-ordered.csv";
        chooser.setSelectedFile(new File(base));
        if (chooser.showSaveDialog(this) != JFileChooser.APPROVE_OPTION) return;
        try {
            Files.write(chooser.getSelectedFile().toPath(), buildCsv(byGroup).getBytes(StandardCharsets.UTF_8));
        } catch (IOException ex) {
            JOptionPane.showMessageDialog(this, "Não consegui salvar o arquivo: " + ex.getMessage(), "Export CSV", JOptionPane.ERROR_MESSAGE);
        }
    }

    private final class Model extends AbstractTableModel {
        @Override public int getRowCount() { return rows.size(); }
        @Override public int getColumnCount() { return COLUMNS.length; }
        @Override public String getColumnName(int c) { return COLUMNS[c]; }
        @Override public Object getValueAt(int r, int c) { return rows.get(r).cells[c]; }
    }

    private final class RowRenderer extends DefaultTableCellRenderer {
        @Override
        public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int col) {
            super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, col);
            Kind kind = rows.get(row).kind;
            setHorizontalAlignment(col >= 2 ? SwingConstants.RIGHT : SwingConstants.LEFT);
            setBorder(new EmptyBorder(0, 8, 0, 8));
            setFont(getFont().deriveFont(kind == Kind.ITEM ? Font.PLAIN : Font.BOLD));
            setForeground(INK);
            setBackground(Color.WHITE);
            if (kind == Kind.GROUP) { setBackground(new Color(0xEE, 0xF2, 0xF6)); }
            else if (kind == Kind.SUBTOTAL) { setBackground(new Color(0xF7, 0xF9, 0xFB)); setForeground(GRAY); }
            else if (kind == Kind.GRAND) { setBackground(INK); setForeground(Color.WHITE); }
            else if (col == 5) { setFont(getFont().deriveFont(Font.BOLD)); }
            if (kind == Kind.ITEM && col == 2) setForeground(ORANGE);
            return this;
        }
    }
}
