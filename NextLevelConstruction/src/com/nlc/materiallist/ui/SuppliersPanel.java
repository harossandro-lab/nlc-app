package com.nlc.materiallist.ui;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Font;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.util.List;

import javax.swing.JButton;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.border.EmptyBorder;
import javax.swing.table.AbstractTableModel;

import com.nlc.materiallist.dao.SupplierDao;
import com.nlc.materiallist.model.Project;
import com.nlc.materiallist.model.Supplier;

public class SuppliersPanel extends JPanel {

    private static final Color INK = new Color(0x10, 0x23, 0x3B);
    private final SupplierDao supplierDao = new SupplierDao();

    public SuppliersPanel(Project project) {
        setLayout(new BorderLayout(0, 12));
        setBackground(Color.WHITE);
        setBorder(new EmptyBorder(20, 24, 20, 24));

        JPanel head = new JPanel(new BorderLayout());
        head.setBackground(Color.WHITE);
        JLabel title = new JLabel("Suppliers & Tax");
        title.setFont(title.getFont().deriveFont(Font.BOLD, 22f));
        title.setForeground(INK);
        head.add(title, BorderLayout.WEST);
        JButton add = new JButton("+ Add supplier");
        add.setBackground(new Color(0xE2, 0x60, 0x0C));
        add.setForeground(Color.WHITE);
        add.setFocusPainted(false);
        head.add(add, BorderLayout.EAST);
        add(head, BorderLayout.NORTH);

        List<Supplier> suppliers = supplierDao.findByProject(project.id);
        Model model = new Model(suppliers);
        JTable table = new JTable(model);
        table.setRowHeight(26);
        table.setFont(table.getFont().deriveFont(12.5f));
        table.getColumnModel().getColumn(3).setCellRenderer(new TableRenderers.DeleteRenderer());

        table.addMouseListener(new MouseAdapter() {
            @Override public void mouseClicked(MouseEvent e) {
                int row = table.rowAtPoint(e.getPoint()), col = table.columnAtPoint(e.getPoint());
                if (row >= 0 && col == 3) model.removeRow(row);
            }
        });
        add.addActionListener(e -> model.addRow(project.id));

        JLabel info = new JLabel("<html>Unit price final = Unit price (no tax) &times; (1 + Tax% do fornecedor).</html>");
        info.setForeground(new Color(0x5B, 0x6B, 0x7A));
        info.setBorder(new EmptyBorder(8, 2, 0, 0));

        add(new JScrollPane(table), BorderLayout.CENTER);
        add(info, BorderLayout.SOUTH);
    }

    private class Model extends AbstractTableModel {
        private final String[] cols = {"Supply (name)", "Tax %", "Delay (days)", ""};
        private final List<Supplier> rows;
        Model(List<Supplier> rows) { this.rows = rows; }

        @Override public int getRowCount() { return rows.size(); }
        @Override public int getColumnCount() { return cols.length; }
        @Override public String getColumnName(int c) { return cols[c]; }
        @Override public boolean isCellEditable(int r, int c) { return c != 3; }

        @Override
        public Object getValueAt(int r, int c) {
            Supplier s = rows.get(r);
            switch (c) { case 0: return s.name; case 1: return s.tax; case 2: return s.delay; case 3: return "×"; default: return ""; }
        }
        @Override
        public void setValueAt(Object value, int r, int c) {
            Supplier s = rows.get(r);
            try {
                switch (c) {
                    case 0: s.name = value.toString(); break;
                    case 1: s.tax = Double.parseDouble(value.toString()); break;
                    case 2: s.delay = Integer.parseInt(value.toString()); break;
                }
            } catch (NumberFormatException ignored) {}
            supplierDao.update(s);
            fireTableRowsUpdated(r, r);
        }
        void addRow(String projectId) {
            Supplier s = supplierDao.insert(projectId, "", 0, 0);
            rows.add(s);
            fireTableRowsInserted(rows.size() - 1, rows.size() - 1);
        }
        void removeRow(int r) {
            Supplier s = rows.remove(r);
            supplierDao.delete(s.id);
            fireTableRowsDeleted(r, r);
        }
    }
}
