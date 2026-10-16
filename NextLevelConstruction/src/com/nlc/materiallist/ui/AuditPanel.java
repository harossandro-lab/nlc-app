package com.nlc.materiallist.ui;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.Font;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;

import javax.swing.BorderFactory;
import javax.swing.JButton;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.SwingConstants;
import javax.swing.border.EmptyBorder;
import javax.swing.table.AbstractTableModel;
import javax.swing.table.DefaultTableCellRenderer;

import com.nlc.materiallist.dao.AuditDao;
import com.nlc.materiallist.model.Project;
import com.nlc.materiallist.service.AuditService;

/**
 * Audit Log: automatic history of quantity changes per ItemKey (ADDED / CHANGED / REMOVED), like the original
 * PRICE_AUDIT sheet. Read-only. Opening it first records any edit that is still waiting for its comparison.
 */
public class AuditPanel extends JPanel {

    private static final Color INK = new Color(0x10, 0x23, 0x3B);
    private static final Color GRAY = new Color(0x5B, 0x6B, 0x7A);
    private static final Color LINE = new Color(0xC7, 0xD2, 0xDB);
    private static final DateTimeFormatter LOCAL_TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss").withZone(ZoneId.systemDefault());

    private static final String[] COLUMNS = {"Timestamp", "Action", "ItemKey", "Old Qty", "New Qty"};

    private final List<AuditDao.Entry> entries;
    private final String projectName;

    public AuditPanel(Project project) {
        this.projectName = project.name;
        setLayout(new BorderLayout(0, 14));
        setBackground(Color.WHITE);
        setBorder(new EmptyBorder(22, 26, 26, 26));

        AuditService.runDiff(project.id);   // catch up with edits whose 1.4 s timer has not fired yet
        entries = new AuditDao().findLog(project.id);

        JLabel heading = new JLabel("Audit Log");
        heading.setFont(heading.getFont().deriveFont(Font.BOLD, 22f));
        heading.setForeground(INK);
        JLabel sub = new JLabel("Histórico automático de alterações de quantidade por ItemKey — como a aba PRICE_AUDIT original.");
        sub.setFont(sub.getFont().deriveFont(Font.PLAIN, 12f));
        sub.setForeground(GRAY);
        JPanel titles = new JPanel(new BorderLayout(0, 4));
        titles.setBackground(Color.WHITE);
        titles.add(heading, BorderLayout.NORTH);
        titles.add(sub, BorderLayout.SOUTH);

        JButton export = new JButton("Export CSV");
        export.addActionListener(e -> Csv.saveWithDialog(this,
                (projectName == null || projectName.isEmpty() ? "project" : projectName) + "-audit-log.csv", buildCsv(entries)));
        JPanel top = new JPanel(new BorderLayout());
        top.setBackground(Color.WHITE);
        top.add(titles, BorderLayout.CENTER);
        top.add(export, BorderLayout.EAST);
        add(top, BorderLayout.NORTH);

        JTable table = new JTable(new Model());
        table.setRowHeight(24);
        table.setShowGrid(false);
        table.setFillsViewportHeight(true);
        table.getTableHeader().setReorderingAllowed(false);
        table.setDefaultRenderer(Object.class, new CellRenderer());
        int[] widths = {170, 90, 380, 80, 80};
        for (int i = 0; i < widths.length; i++) table.getColumnModel().getColumn(i).setPreferredWidth(widths[i]);
        JScrollPane scroll = new JScrollPane(table);
        scroll.setBorder(BorderFactory.createLineBorder(LINE));
        if (entries.isEmpty()) {
            JLabel empty = new JLabel("Nenhuma mudança registrada ainda. O log é gerado automaticamente ao adicionar, editar ou remover linhas de takeoff.");
            empty.setForeground(GRAY);
            empty.setBorder(new EmptyBorder(10, 2, 0, 0));
            add(empty, BorderLayout.SOUTH);
        }
        add(scroll, BorderLayout.CENTER);
    }

    /** CSV as the web app exports it: raw ISO timestamp, empty Old Qty for ADDED. */
    public static String buildCsv(List<AuditDao.Entry> entries) {
        StringBuilder sb = new StringBuilder("Timestamp,Action,ItemKey,Old Qty,New Qty\n");
        for (AuditDao.Entry a : entries) {
            Csv.appendRow(sb, a.ts, a.action, a.itemKey, a.oldQty == null ? "" : String.valueOf(a.oldQty), String.valueOf(a.newQty));
        }
        return sb.toString();
    }

    static String localTime(String iso) {
        try { return LOCAL_TIME.format(Instant.parse(iso)); }
        catch (RuntimeException e) { return iso; }
    }

    private final class Model extends AbstractTableModel {
        @Override public int getRowCount() { return entries.size(); }
        @Override public int getColumnCount() { return COLUMNS.length; }
        @Override public String getColumnName(int c) { return COLUMNS[c]; }
        @Override
        public Object getValueAt(int r, int c) {
            AuditDao.Entry a = entries.get(r);
            switch (c) {
                case 0: return localTime(a.ts);
                case 1: return a.action;
                case 2: return a.itemKey;
                case 3: return a.oldQty == null ? "—" : String.valueOf(a.oldQty);
                case 4: return String.valueOf(a.newQty);
                default: return "";
            }
        }
    }

    /** Action column is colored like the status pills elsewhere. */
    private final class CellRenderer extends DefaultTableCellRenderer {
        @Override
        public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int col) {
            super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, col);
            setBorder(new EmptyBorder(0, 8, 0, 8));
            setHorizontalAlignment(col >= 3 ? SwingConstants.RIGHT : SwingConstants.LEFT);
            setFont(table.getFont());
            setForeground(INK);
            if (col == 1 && !isSelected) {
                String action = String.valueOf(value);
                setFont(getFont().deriveFont(Font.BOLD, 11f));
                if ("ADDED".equals(action)) setForeground(new Color(0x2F, 0x7A, 0x4D));
                else if ("REMOVED".equals(action)) setForeground(new Color(0xB2, 0x3A, 0x2E));
                else setForeground(new Color(0xB9, 0x79, 0x0E));
            } else if (col == 0 || col == 3) {
                setForeground(GRAY);
            }
            return this;
        }
    }
}
