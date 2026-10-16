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

import com.nlc.materiallist.dao.MaterialDbDao;
import com.nlc.materiallist.dao.SupplierDao;
import com.nlc.materiallist.data.SeedData;
import com.nlc.materiallist.model.MaterialDbEntry;
import com.nlc.materiallist.model.Project;
import com.nlc.materiallist.model.Supplier;

public class MaterialsDbPanel extends JPanel {

    private static final Color INK = new Color(0x10, 0x23, 0x3B);

    private final Project project;
    private final MaterialDbDao materialDao = new MaterialDbDao();
    private final SupplierDao supplierDao = new SupplierDao();

    public MaterialsDbPanel(Project project) {
        this.project = project;
        setLayout(new BorderLayout(0, 12));
        setBackground(Color.WHITE);
        setBorder(new EmptyBorder(20, 24, 20, 24));

        JPanel head = new JPanel(new BorderLayout());
        head.setBackground(Color.WHITE);
        JLabel title = new JLabel("Materials Database");
        title.setFont(title.getFont().deriveFont(Font.BOLD, 22f));
        title.setForeground(INK);
        head.add(title, BorderLayout.WEST);
        JButton add = new JButton("+ Add material");
        add.setBackground(new Color(0xE2, 0x60, 0x0C));
        add.setForeground(Color.WHITE);
        add.setFocusPainted(false);
        head.add(add, BorderLayout.EAST);
        add(head, BorderLayout.NORTH);

        List<MaterialDbEntry> entries = materialDao.findByProject(project.id);
        List<Supplier> suppliers = supplierDao.findByProject(project.id);
        Model model = new Model(entries, suppliers);
        JTable table = new JTable(model);
        table.setRowHeight(26);
        table.setFont(table.getFont().deriveFont(12.5f));
        table.getColumnModel().getColumn(3).setCellEditor(new SuggestCellEditor(namesOf(suppliers), false));
        table.getColumnModel().getColumn(1).setCellEditor(new SuggestCellEditor(SeedData.LENGTHS, true));
        table.getColumnModel().getColumn(2).setCellEditor(new SuggestCellEditor(SeedData.SPECIES, true));
        table.getColumnModel().getColumn(6).setCellRenderer(new TableRenderers.DeleteRenderer());

        table.addMouseListener(new MouseAdapter() {
            @Override public void mouseClicked(MouseEvent e) {
                int row = table.rowAtPoint(e.getPoint()), col = table.columnAtPoint(e.getPoint());
                if (row >= 0 && col == 6) model.removeRow(row);
            }
        });

        add.addActionListener(e -> model.addRow(project.id));

        add(new JScrollPane(table), BorderLayout.CENTER);
    }

    private List<String> namesOf(List<Supplier> suppliers) {
        return suppliers.stream().map(s -> s.name).toList();
    }

    private class Model extends AbstractTableModel {
        private final String[] cols = {"Material", "Length", "Species", "Supply", "Unit $ (no tax)", "Unit $ (final)", ""};
        private final List<MaterialDbEntry> rows;
        private final List<Supplier> suppliers;

        Model(List<MaterialDbEntry> rows, List<Supplier> suppliers) { this.rows = rows; this.suppliers = suppliers; }

        @Override public int getRowCount() { return rows.size(); }
        @Override public int getColumnCount() { return cols.length; }
        @Override public String getColumnName(int c) { return cols[c]; }
        @Override public boolean isCellEditable(int r, int c) { return c != 5 && c != 6; }

        @Override
        public Object getValueAt(int r, int c) {
            MaterialDbEntry d = rows.get(r);
            switch (c) {
                case 0: return d.material;
                case 1: return d.length;
                case 2: return d.species;
                case 3: return d.supply;
                case 4: return d.unitPriceOutTax;
                case 5:
                    Double u = com.nlc.materiallist.calc.CalcEngine.unitPriceOf(d, suppliers);
                    return u == null ? "—" : String.format("%.2f", u);
                case 6: return "×";
                default: return "";
            }
        }

        @Override
        public void setValueAt(Object value, int r, int c) {
            MaterialDbEntry d = rows.get(r);
            switch (c) {
                case 0: d.material = value.toString(); break;
                case 1: d.length = value.toString(); break;
                case 2: d.species = value.toString(); break;
                case 3: d.supply = value.toString(); break;
                case 4: try { d.unitPriceOutTax = Double.parseDouble(value.toString()); } catch (Exception ignored) {} break;
            }
            materialDao.update(d);
            fireTableRowsUpdated(r, r);
        }

        void addRow(String projectId) {
            MaterialDbEntry d = new MaterialDbEntry();
            d.projectId = projectId; d.supply = "FACTORY";
            materialDao.insert(d);
            rows.add(d);
            fireTableRowsInserted(rows.size() - 1, rows.size() - 1);
        }
        void removeRow(int r) {
            MaterialDbEntry d = rows.remove(r);
            materialDao.delete(d.id);
            fireTableRowsDeleted(r, r);
        }
    }
}
