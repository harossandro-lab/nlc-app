package com.nlc.materiallist.ui;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import javax.swing.BorderFactory;
import javax.swing.JButton;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JProgressBar;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.border.EmptyBorder;
import javax.swing.table.AbstractTableModel;

import com.nlc.materiallist.calc.CalcEngine;
import com.nlc.materiallist.calc.CalcEngine.OrderedLine;
import com.nlc.materiallist.calc.SectionOrder;
import com.nlc.materiallist.dao.MaterialDbDao;
import com.nlc.materiallist.dao.ReceivedDao;
import com.nlc.materiallist.dao.SupplierDao;
import com.nlc.materiallist.dao.TakeoffItemDao;
import com.nlc.materiallist.data.SeedData;
import com.nlc.materiallist.model.MaterialDbEntry;
import com.nlc.materiallist.model.Project;
import com.nlc.materiallist.model.ReceivedEntry;
import com.nlc.materiallist.model.Supplier;

/**
 * Received: delivery log (group, location, supply, date, material, length, species, qty, ticket, invoice, payment)
 * with the line total taken from the Materials DB, plus "Delivered vs Ordered" by group. Every edit is saved at once.
 */
public class ReceivedPanel extends JPanel {

    private static final Color INK = new Color(0x10, 0x23, 0x3B);
    private static final Color GRAY = new Color(0x5B, 0x6B, 0x7A);
    private static final Color GREEN = new Color(0x2F, 0x7A, 0x4D);

    private static final String[] COLUMNS = {"Group", "Location", "Supply", "Date", "Material", "Length", "Species",
            "Qty", "Ticket #", "Invoice #", "Payment", "Total", ""};
    private static final int COL_TOTAL = 11, COL_DELETE = 12;

    private final ReceivedDao dao = new ReceivedDao();
    private final List<MaterialDbEntry> database;
    private final List<Supplier> suppliers;
    private final Map<String, Map<String, OrderedLine>> ordered;
    private final List<ReceivedEntry> rows;
    private final JPanel summary = new JPanel(new GridBagLayout());

    public ReceivedPanel(Project project) {
        setLayout(new BorderLayout(0, 14));
        setBackground(Color.WHITE);
        setBorder(new EmptyBorder(22, 26, 26, 26));

        database = new MaterialDbDao().findByProject(project.id);
        suppliers = new SupplierDao().findByProject(project.id);
        ordered = CalcEngine.aggregateByGroup(
                SectionOrder.sort(new TakeoffItemDao().findByProject(project.id)), database, suppliers);
        rows = dao.findByProject(project.id);

        JLabel heading = new JLabel("Received");
        heading.setFont(heading.getFont().deriveFont(Font.BOLD, 22f));
        heading.setForeground(INK);
        JLabel sub = new JLabel("Registro de entregas — ticket, nota fiscal e data, comparado ao pedido (Ordered).");
        sub.setFont(sub.getFont().deriveFont(Font.PLAIN, 12f));
        sub.setForeground(GRAY);
        JPanel titles = new JPanel(new BorderLayout(0, 4));
        titles.setBackground(Color.WHITE);
        titles.add(heading, BorderLayout.NORTH);
        titles.add(sub, BorderLayout.SOUTH);

        JButton add = new JButton("+ Add delivery");
        add.setBackground(new Color(0xE2, 0x60, 0x0C));
        add.setForeground(Color.WHITE);
        add.setFocusPainted(false);
        JPanel top = new JPanel(new BorderLayout());
        top.setBackground(Color.WHITE);
        top.add(titles, BorderLayout.CENTER);
        top.add(add, BorderLayout.EAST);
        add(top, BorderLayout.NORTH);

        Model model = new Model();
        JTable table = new JTable(model);
        table.setRowHeight(26);
        table.setFillsViewportHeight(true);
        table.getTableHeader().setReorderingAllowed(false);
        table.getColumnModel().getColumn(0).setCellEditor(new SuggestCellEditor(SeedData.GROUPS, false));
        table.getColumnModel().getColumn(1).setCellEditor(new SuggestCellEditor(SeedData.LOCATIONS, true));
        List<String> supplierNames = new ArrayList<>();
        for (Supplier s : suppliers) if (s.name != null && !s.name.isEmpty()) supplierNames.add(s.name);
        table.getColumnModel().getColumn(2).setCellEditor(new SuggestCellEditor(supplierNames, true));
        table.getColumnModel().getColumn(5).setCellEditor(new SuggestCellEditor(SeedData.LENGTHS, true));
        table.getColumnModel().getColumn(6).setCellEditor(new SuggestCellEditor(SeedData.SPECIES, true));
        table.getColumnModel().getColumn(COL_TOTAL).setCellRenderer(new TableRenderers.ComputedRenderer());
        table.getColumnModel().getColumn(COL_DELETE).setCellRenderer(new TableRenderers.DeleteRenderer());
        int[] widths = {170, 80, 90, 95, 130, 60, 80, 55, 80, 80, 80, 90, 30};
        for (int i = 0; i < widths.length; i++) table.getColumnModel().getColumn(i).setPreferredWidth(widths[i]);
        table.setAutoResizeMode(JTable.AUTO_RESIZE_ALL_COLUMNS);

        table.addMouseListener(new MouseAdapter() {
            @Override public void mouseClicked(MouseEvent e) {
                int row = table.rowAtPoint(e.getPoint()), col = table.columnAtPoint(e.getPoint());
                if (row >= 0 && col == COL_DELETE) {
                    if (table.isEditing()) table.getCellEditor().stopCellEditing();
                    model.removeRow(row);
                }
            }
        });
        add.addActionListener(e -> model.addRow(project.id));

        summary.setBackground(Color.WHITE);
        model.addTableModelListener(e -> rebuildSummary());
        rebuildSummary();

        JPanel south = new JPanel(new BorderLayout(0, 8));
        south.setBackground(Color.WHITE);
        JLabel summaryTitle = new JLabel("DELIVERED VS ORDERED — BY GROUP");
        summaryTitle.setFont(summaryTitle.getFont().deriveFont(Font.BOLD, 12f));
        summaryTitle.setForeground(GRAY);
        south.add(summaryTitle, BorderLayout.NORTH);
        JScrollPane summaryScroll = new JScrollPane(summary);
        summaryScroll.setBorder(BorderFactory.createEmptyBorder());
        summaryScroll.setPreferredSize(new Dimension(10, 150));
        south.add(summaryScroll, BorderLayout.CENTER);

        JScrollPane scroll = new JScrollPane(table);
        add(scroll, BorderLayout.CENTER);
        add(south, BorderLayout.SOUTH);
    }

    /** One bar per GROUP that has an order: delivered value / ordered value (same as the web app). */
    private void rebuildSummary() {
        summary.removeAll();
        GridBagConstraints c = new GridBagConstraints();
        c.gridy = 0; c.insets = new Insets(3, 0, 3, 12); c.anchor = GridBagConstraints.WEST;
        boolean any = false;
        for (String g : SeedData.GROUPS) {
            Map<String, OrderedLine> lines = ordered.get(g);
            if (lines == null) continue;
            any = true;
            double orderedTotal = CalcEngine.orderedTotal(lines);
            double delivered = CalcEngine.deliveredTotal(g, rows, database, suppliers);
            JProgressBar bar = new JProgressBar(0, 100);
            bar.setValue((int) Math.round(CalcEngine.deliveredPercent(delivered, orderedTotal)));
            bar.setForeground(GREEN);
            bar.setPreferredSize(new Dimension(260, 10));
            c.gridx = 0; c.weightx = 0; summary.add(new JLabel(g), c);
            c.gridx = 1; summary.add(bar, c);
            c.gridx = 2; c.weightx = 1;
            JLabel amt = new JLabel(CalcEngine.money(delivered) + " / " + CalcEngine.money(orderedTotal));
            amt.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 12));
            summary.add(amt, c);
            c.gridy++;
        }
        if (!any) {
            c.gridx = 0;
            JLabel none = new JLabel("Sem dados de pedido ainda.");
            none.setForeground(GRAY);
            summary.add(none, c);
        }
        summary.revalidate();
        summary.repaint();
    }

    private static String qtyText(Double q) {
        if (q == null) return "";
        return q == Math.rint(q) ? String.valueOf((long) (double) q) : String.valueOf(q);
    }

    private final class Model extends AbstractTableModel {
        @Override public int getRowCount() { return rows.size(); }
        @Override public int getColumnCount() { return COLUMNS.length; }
        @Override public String getColumnName(int c) { return COLUMNS[c]; }
        @Override public boolean isCellEditable(int r, int c) { return c != COL_TOTAL && c != COL_DELETE; }

        @Override
        public Object getValueAt(int r, int c) {
            ReceivedEntry e = rows.get(r);
            switch (c) {
                case 0: return e.group;
                case 1: return e.location;
                case 2: return e.supply;
                case 3: return e.date;
                case 4: return e.material;
                case 5: return e.length;
                case 6: return e.species;
                case 7: return qtyText(e.qty);
                case 8: return e.ticket;
                case 9: return e.invoice;
                case 10: return e.payment;
                case COL_TOTAL: {
                    Double t = CalcEngine.receivedLineTotal(e, database, suppliers);
                    return t == null ? "—" : CalcEngine.money(t);
                }
                case COL_DELETE: return "×";
                default: return "";
            }
        }

        @Override
        public void setValueAt(Object value, int r, int c) {
            ReceivedEntry e = rows.get(r);
            String v = value == null ? "" : value.toString().trim();
            switch (c) {
                case 0: e.group = v; break;
                case 1: e.location = v; break;
                case 2: e.supply = v; break;
                case 3:
                    if (!v.isEmpty()) {
                        try { LocalDate.parse(v); }
                        catch (DateTimeParseException ex) { java.awt.Toolkit.getDefaultToolkit().beep(); return; }  // keep the old date
                    }
                    e.date = v; break;
                case 4: e.material = v; break;
                case 5: e.length = v; break;
                case 6: e.species = v; break;
                case 7:
                    if (v.isEmpty()) e.qty = null;
                    else {
                        try { e.qty = Double.parseDouble(v); }
                        catch (NumberFormatException ex) { java.awt.Toolkit.getDefaultToolkit().beep(); return; }
                    }
                    break;
                case 8: e.ticket = v; break;
                case 9: e.invoice = v; break;
                case 10: e.payment = v; break;
                default: return;
            }
            dao.update(e);
            fireTableRowsUpdated(r, r);
        }

        void addRow(String projectId) {
            ReceivedEntry e = new ReceivedEntry();
            e.projectId = projectId;
            dao.insert(e);
            rows.add(0, e);   // newest on top, like the web app
            fireTableRowsInserted(0, 0);
        }

        void removeRow(int r) {
            ReceivedEntry e = rows.remove(r);
            dao.delete(e.id);
            fireTableRowsDeleted(r, r);
        }
    }
}
