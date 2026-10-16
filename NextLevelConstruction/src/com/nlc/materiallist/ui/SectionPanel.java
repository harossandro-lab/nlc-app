package com.nlc.materiallist.ui;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Font;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.List;

import javax.swing.JButton;
import javax.swing.JFileChooser;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.JTextField;
import javax.swing.SwingConstants;
import javax.swing.border.EmptyBorder;
import javax.swing.event.DocumentEvent;
import javax.swing.event.DocumentListener;
import javax.swing.table.TableRowSorter;

import com.nlc.materiallist.calc.CalcEngine;
import com.nlc.materiallist.dao.MaterialDbDao;
import com.nlc.materiallist.dao.SupplierDao;
import com.nlc.materiallist.dao.TakeoffItemDao;
import com.nlc.materiallist.data.SeedData;
import com.nlc.materiallist.model.MaterialDbEntry;
import com.nlc.materiallist.model.Project;
import com.nlc.materiallist.model.Supplier;
import com.nlc.materiallist.model.TakeoffItem;

/**
 * Editable table for one take-off section. Fully generic over sectionId — this same class
 * renders Sub-Floor today and, unchanged, any of the other 12 sections in SeedData.SECTIONS
 * once a tile for them is added to ProjectMenuPanel.
 */
public class SectionPanel extends JPanel {

    private static final Color INK = new Color(0x10, 0x23, 0x3B);
    private static final Color GRAY = new Color(0x5B, 0x6B, 0x7A);
    private static final Color LINE = new Color(0xC7, 0xD2, 0xDB);

    private final Project project;
    private final SeedData.Section section;
    private final TakeoffItemDao itemDao = new TakeoffItemDao();
    private final MaterialDbDao materialDao = new MaterialDbDao();
    private final SupplierDao supplierDao = new SupplierDao();

    private TakeoffTableModel model;
    private JTable table;
    private JLabel subLabel;

    public SectionPanel(Project project, String sectionId) {
        this.project = project;
        this.section = findSection(sectionId);

        setLayout(new BorderLayout(0, 12));
        setBackground(Color.WHITE);
        setBorder(new EmptyBorder(20, 24, 20, 24));

        add(header(), BorderLayout.NORTH);
        add(buildTable(), BorderLayout.CENTER);
    }

    private SeedData.Section findSection(String id) {
        for (SeedData.Section s : SeedData.SECTIONS) if (s.id.equals(id)) return s;
        throw new IllegalArgumentException("Unknown section: " + id);
    }

    private JPanel header() {
        JPanel head = new JPanel(new BorderLayout());
        head.setBackground(Color.WHITE);

        JPanel left = new JPanel();
        left.setLayout(new javax.swing.BoxLayout(left, javax.swing.BoxLayout.Y_AXIS));
        left.setBackground(Color.WHITE);
        JLabel title = new JLabel(section.label);
        title.setFont(title.getFont().deriveFont(Font.BOLD, 22f));
        title.setForeground(INK);
        subLabel = new JLabel();
        subLabel.setFont(subLabel.getFont().deriveFont(11.5f));
        subLabel.setForeground(GRAY);
        left.add(title);
        left.add(subLabel);
        head.add(left, BorderLayout.WEST);

        JPanel right = new JPanel();
        right.setBackground(Color.WHITE);

        JTextField search = new JTextField(14);
        search.setBorder(javax.swing.BorderFactory.createCompoundBorder(
                javax.swing.BorderFactory.createLineBorder(LINE), new EmptyBorder(5, 8, 5, 8)));

        JButton export = ghostButton("Export CSV");
        JButton addLine = accentButton("+ Add line");

        right.add(search);
        right.add(export);
        right.add(addLine);
        head.add(right, BorderLayout.EAST);

        addLine.addActionListener(e -> {
            String defaultGroup = SeedData.DEFAULT_GROUP.getOrDefault(section.id, "");
            model.addRow(defaultGroup);
            updateSubLabel();
            int lastRow = table.convertRowIndexToView(model.getRowCount() - 1);
            table.scrollRectToVisible(table.getCellRect(lastRow, 0, true));
            table.editCellAt(lastRow, TakeoffTableModel.COL_PURPOSE);
        });
        export.addActionListener(e -> exportCsv());
        search.getDocument().addDocumentListener(new DocumentListener() {
            private void apply() { applyFilter(search.getText()); }
            @Override public void insertUpdate(DocumentEvent e) { apply(); }
            @Override public void removeUpdate(DocumentEvent e) { apply(); }
            @Override public void changedUpdate(DocumentEvent e) { apply(); }
        });

        return head;
    }

    private TableRowSorter<TakeoffTableModel> sorter;

    private JScrollPane buildTable() {
        List<TakeoffItem> items = itemDao.findBySection(project.id, section.id);
        model = new TakeoffTableModel(project.id, section.id, items, itemDao, materialDao, supplierDao);
        table = new JTable(model);
        table.setRowHeight(26);
        table.setFont(table.getFont().deriveFont(12.5f));
        table.setGridColor(new Color(0xE3, 0xE9, 0xEE));
        table.setSelectionBackground(new Color(0xEA, 0xF1, 0xF8));
        table.getTableHeader().setFont(table.getFont().deriveFont(Font.BOLD, 10.5f));
        table.getTableHeader().setBackground(new Color(0xEA, 0xF1, 0xF8));
        table.setAutoResizeMode(JTable.AUTO_RESIZE_OFF);

        sorter = new TableRowSorter<>(model);
        table.setRowSorter(sorter);

        // Column widths, roughly matching the web app's column proportions
        int[] widths = {130, 140, 70, 150, 70, 90, 50, 50, 70, 50, 50, 80, 65, 80, 90, 30};
        for (int i = 0; i < widths.length; i++) table.getColumnModel().getColumn(i).setPreferredWidth(widths[i]);

        table.getColumnModel().getColumn(TakeoffTableModel.COL_GROUP)
                .setCellEditor(new SuggestCellEditor(SeedData.GROUPS, false));
        table.getColumnModel().getColumn(TakeoffTableModel.COL_PURPOSE)
                .setCellEditor(new SuggestCellEditor(section.purposes, true));
        table.getColumnModel().getColumn(TakeoffTableModel.COL_MATERIAL)
                .setCellEditor(new MaterialCellEditor());
        table.getColumnModel().getColumn(TakeoffTableModel.COL_LENGTH)
                .setCellEditor(new SuggestCellEditor(SeedData.LENGTHS, true));
        table.getColumnModel().getColumn(TakeoffTableModel.COL_SPECIES)
                .setCellEditor(new SuggestCellEditor(SeedData.SPECIES, true));
        table.getColumnModel().getColumn(TakeoffTableModel.COL_SP)
                .setCellEditor(new SuggestCellEditor(SeedData.SPACINGS, true));
        table.getColumnModel().getColumn(TakeoffTableModel.COL_LOCATION)
                .setCellEditor(new SuggestCellEditor(SeedData.LOCATIONS, true));

        table.getColumnModel().getColumn(TakeoffTableModel.COL_QTY).setCellRenderer(new TableRenderers.ComputedRenderer());
        table.getColumnModel().getColumn(TakeoffTableModel.COL_UNIT).setCellRenderer(new TableRenderers.ComputedRenderer());
        table.getColumnModel().getColumn(TakeoffTableModel.COL_TOTAL).setCellRenderer(new TableRenderers.ComputedRenderer());
        table.getColumnModel().getColumn(TakeoffTableModel.COL_STATUS).setCellRenderer(new TableRenderers.StatusRenderer());
        table.getColumnModel().getColumn(TakeoffTableModel.COL_DELETE).setCellRenderer(new TableRenderers.DeleteRenderer());

        table.addMouseListener(new MouseAdapter() {
            @Override public void mouseClicked(MouseEvent e) {
                int viewRow = table.rowAtPoint(e.getPoint());
                int viewCol = table.columnAtPoint(e.getPoint());
                if (viewRow < 0 || viewCol < 0) return;
                int modelRow = table.convertRowIndexToModel(viewRow);
                if (viewCol == TakeoffTableModel.COL_STATUS) {
                    model.cycleStatus(modelRow);
                    updateSubLabel();
                } else if (viewCol == TakeoffTableModel.COL_DELETE) {
                    model.removeRow(modelRow);
                    updateSubLabel();
                }
            }
        });

        // Repaint totals whenever any edit happens (QTY/Unit/Total already recompute on read)
        model.addTableModelListener(e -> updateSubLabel());

        updateSubLabel();
        return new JScrollPane(table);
    }

    private void applyFilter(String text) {
        if (text == null || text.isBlank()) { sorter.setRowFilter(null); return; }
        try {
            sorter.setRowFilter(javax.swing.RowFilter.regexFilter("(?i)" + java.util.regex.Pattern.quote(text)));
        } catch (Exception ignored) {}
    }

    private void refresh() {
        List<TakeoffItem> items = itemDao.findBySection(project.id, section.id);
        model = new TakeoffTableModel(project.id, section.id, items, itemDao, materialDao, supplierDao);
        table.setModel(model);
        // re-attach editors/renderers since setModel doesn't clear column customizations, but
        // rebuilding the table wholesale is simpler and this panel is small enough that it's instant.
        removeAll();
        add(header(), BorderLayout.NORTH);
        add(buildTable(), BorderLayout.CENTER);
        revalidate();
        repaint();
    }

    private void updateSubLabel() {
        List<TakeoffItem> items = itemDao.findBySection(project.id, section.id);
        double total = 0;
        List<MaterialDbEntry> db = materialDao.findByProject(project.id);
        List<Supplier> sup = supplierDao.findByProject(project.id);
        for (TakeoffItem it : items) {
            Double t = CalcEngine.lineTotal(it, db, sup);
            if (t != null) total += t;
        }
        subLabel.setText(items.size() + " line item(s) · estimated " + String.format("$%,.2f", total));
    }

    private void exportCsv() {
        JFileChooser chooser = new JFileChooser();
        chooser.setSelectedFile(new java.io.File(project.name + "-" + section.id + ".csv"));
        if (chooser.showSaveDialog(this) != JFileChooser.APPROVE_OPTION) return;
        List<TakeoffItem> items = itemDao.findBySection(project.id, section.id);
        List<MaterialDbEntry> db = materialDao.findByProject(project.id);
        List<Supplier> sup = supplierDao.findByProject(project.id);
        try (PrintWriter w = new PrintWriter(new FileWriter(chooser.getSelectedFile()))) {
            w.println("Group,Purpose,Page/Detail,Material,Length,Species,LF,SF,SP,EA,QTY,Location,ItemKey,Unit Price,Total,Status");
            for (TakeoffItem it : items) {
                Integer qty = CalcEngine.computeQty(it);
                MaterialDbEntry d = CalcEngine.findDbEntry(it, db);
                Double unit = CalcEngine.unitPriceOf(d, sup);
                Double total = CalcEngine.lineTotal(it, db, sup);
                w.println(String.join(",",
                        csv(it.group), csv(it.purpose), csv(it.pageDetail), csv(it.material), csv(it.length), csv(it.species),
                        csv(it.lf), csv(it.sf), csv(it.sp), csv(it.ea), csv(qty), csv(it.location),
                        csv(CalcEngine.buildItemKey(it.material, it.length, it.species)),
                        csv(unit), csv(total), csv(it.status)));
            }
            JOptionPane.showMessageDialog(this, "Exported to " + chooser.getSelectedFile().getName());
        } catch (IOException ex) {
            JOptionPane.showMessageDialog(this, "Could not export: " + ex.getMessage(), "Export failed", JOptionPane.ERROR_MESSAGE);
        }
    }

    private static String csv(Object v) {
        String s = v == null ? "" : v.toString();
        if (s.contains(",") || s.contains("\"") || s.contains("\n")) s = "\"" + s.replace("\"", "\"\"") + "\"";
        return s;
    }

    private JButton accentButton(String text) {
        JButton b = new JButton(text);
        b.setBackground(new Color(0xE2, 0x60, 0x0C));
        b.setForeground(Color.WHITE);
        b.setFocusPainted(false);
        b.setFont(b.getFont().deriveFont(Font.BOLD, 12f));
        return b;
    }
    private JButton ghostButton(String text) {
        JButton b = new JButton(text);
        b.setBackground(Color.WHITE);
        b.setForeground(INK);
        b.setFocusPainted(false);
        return b;
    }
}
