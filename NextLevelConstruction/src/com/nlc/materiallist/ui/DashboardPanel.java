package com.nlc.materiallist.ui;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Font;
import java.awt.GridLayout;
import java.util.List;

import javax.swing.BorderFactory;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JTextField;
import javax.swing.border.EmptyBorder;
import javax.swing.event.DocumentEvent;
import javax.swing.event.DocumentListener;

import com.nlc.materiallist.calc.CalcEngine;
import com.nlc.materiallist.dao.MaterialDbDao;
import com.nlc.materiallist.dao.ProjectDao;
import com.nlc.materiallist.dao.SupplierDao;
import com.nlc.materiallist.dao.TakeoffItemDao;
import com.nlc.materiallist.model.MaterialDbEntry;
import com.nlc.materiallist.model.Project;
import com.nlc.materiallist.model.ProjectInfo;
import com.nlc.materiallist.model.Supplier;
import com.nlc.materiallist.model.TakeoffItem;

public class DashboardPanel extends JPanel {

    private static final Color INK = new Color(0x10, 0x23, 0x3B);
    private static final Color GRAY = new Color(0x5B, 0x6B, 0x7A);
    private static final Color ORANGE = new Color(0xE2, 0x60, 0x0C);
    private static final Color LINE = new Color(0xC7, 0xD2, 0xDB);

    private final ProjectDao projectDao = new ProjectDao();
    private final TakeoffItemDao itemDao = new TakeoffItemDao();
    private final MaterialDbDao materialDao = new MaterialDbDao();
    private final SupplierDao supplierDao = new SupplierDao();

    public DashboardPanel(Project project) {
        setLayout(new BorderLayout(0, 18));
        setBackground(Color.WHITE);
        setBorder(new EmptyBorder(22, 26, 26, 26));

        JLabel heading = new JLabel("Dashboard");
        heading.setFont(heading.getFont().deriveFont(Font.BOLD, 22f));
        heading.setForeground(INK);
        add(heading, BorderLayout.NORTH);

        JPanel body = new JPanel();
        body.setLayout(new javax.swing.BoxLayout(body, javax.swing.BoxLayout.Y_AXIS));
        body.setBackground(Color.WHITE);
        body.add(kpiRow(project));
        body.add(javax.swing.Box.createVerticalStrut(20));
        body.add(titleBlock(project));
        add(new javax.swing.JScrollPane(body), BorderLayout.CENTER);
    }

    private JPanel kpiRow(Project project) {
        List<TakeoffItem> items = itemDao.findByProject(project.id);
        List<MaterialDbEntry> database = materialDao.findByProject(project.id);
        List<Supplier> suppliers = supplierDao.findByProject(project.id);

        double total = 0, ordered = 0, received = 0;
        for (TakeoffItem it : items) {
            Double t = CalcEngine.lineTotal(it, database, suppliers);
            if (t != null) {
                total += t;
                if ("ordered".equals(it.status)) ordered += t;
                if ("received".equals(it.status)) received += t;
            }
        }

        JPanel row = new JPanel(new GridLayout(1, 4, 12, 0));
        row.setBackground(Color.WHITE);
        row.add(kpiCard("Line items", String.valueOf(items.size()), null, INK));
        row.add(kpiCard("Estimated total", money(total), null, ORANGE));
        row.add(kpiCard("Ordered value", money(ordered), pct(ordered, total) + "% of total", new Color(0xB9, 0x79, 0x0E)));
        row.add(kpiCard("Received value", money(received), pct(received, total) + "% of total", new Color(0x2F, 0x7A, 0x4D)));
        return row;
    }

    private JPanel kpiCard(String label, String value, String sub, Color accent) {
        JPanel card = new JPanel();
        card.setLayout(new javax.swing.BoxLayout(card, javax.swing.BoxLayout.Y_AXIS));
        card.setBackground(Color.WHITE);
        card.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createMatteBorder(0, 4, 0, 0, accent),
                BorderFactory.createCompoundBorder(
                        BorderFactory.createLineBorder(LINE),
                        new EmptyBorder(12, 12, 12, 12))));
        JLabel l = new JLabel(label.toUpperCase());
        l.setFont(l.getFont().deriveFont(Font.PLAIN, 10.5f));
        l.setForeground(GRAY);
        JLabel v = new JLabel(value);
        v.setFont(new Font(Font.MONOSPACED, Font.BOLD, 22));
        v.setForeground(INK);
        card.add(l);
        card.add(javax.swing.Box.createVerticalStrut(6));
        card.add(v);
        if (sub != null) {
            JLabel s = new JLabel(sub);
            s.setFont(s.getFont().deriveFont(Font.PLAIN, 11f));
            s.setForeground(GRAY);
            card.add(s);
        }
        return card;
    }

    private JPanel titleBlock(Project project) {
        ProjectInfo info = projectDao.getInfo(project.id);
        JPanel panel = new JPanel(new GridLayout(0, 2, 24, 14));
        panel.setBackground(Color.WHITE);
        panel.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(LINE), new EmptyBorder(16, 18, 16, 18)));

        panel.add(field("Project Name", info.name, v -> { info.name = v; projectDao.saveInfo(project.id, info); }));
        panel.add(field("Jobsite Location", info.jobsite, v -> { info.jobsite = v; projectDao.saveInfo(project.id, info); }));
        panel.add(field("Builder Name", info.builder, v -> { info.builder = v; projectDao.saveInfo(project.id, info); }));
        panel.add(field("Created By", info.createdBy, v -> { info.createdBy = v; projectDao.saveInfo(project.id, info); }));
        panel.add(field("Architectural Plan Date", info.archDate, v -> { info.archDate = v; projectDao.saveInfo(project.id, info); }));
        panel.add(field("Structural Plan Date", info.structDate, v -> { info.structDate = v; projectDao.saveInfo(project.id, info); }));
        panel.add(field("Total Square Feet", info.totalSF, v -> { info.totalSF = v; projectDao.saveInfo(project.id, info); }));
        return panel;
    }

    private JPanel field(String label, String value, java.util.function.Consumer<String> onChange) {
        JPanel wrap = new JPanel(new BorderLayout(0, 4));
        wrap.setBackground(Color.WHITE);
        JLabel l = new JLabel(label.toUpperCase());
        l.setFont(l.getFont().deriveFont(Font.PLAIN, 10f));
        l.setForeground(GRAY);
        JTextField field = new JTextField(value == null ? "" : value);
        field.setBorder(BorderFactory.createMatteBorder(0, 0, 1, 0, LINE));
        field.getDocument().addDocumentListener(new DocumentListener() {
            @Override public void insertUpdate(DocumentEvent e) { onChange.accept(field.getText()); }
            @Override public void removeUpdate(DocumentEvent e) { onChange.accept(field.getText()); }
            @Override public void changedUpdate(DocumentEvent e) { onChange.accept(field.getText()); }
        });
        wrap.add(l, BorderLayout.NORTH);
        wrap.add(field, BorderLayout.CENTER);
        return wrap;
    }

    private static String money(double n) { return String.format("$%,.2f", n); }
    private static long pct(double part, double total) { return total == 0 ? 0 : Math.round(part / total * 100); }
}
