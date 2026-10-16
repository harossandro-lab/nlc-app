package com.nlc.materiallist.ui;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.GridLayout;
import java.util.List;
import java.util.function.Consumer;

import javax.swing.BorderFactory;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JTextField;
import javax.swing.SwingConstants;

import com.nlc.materiallist.dao.ProjectDao;
import com.nlc.materiallist.model.Project;

/** Home screen: "+ New Job" tile followed by one circle per project. Mirrors the web app 1:1. */
public class HomePanel extends JPanel {

    private final ProjectDao projectDao = new ProjectDao();
    private final JPanel grid = new JPanel(new GridLayout(0, 3, 24, 24));
    private final Consumer<Project> onOpenProject;

    public HomePanel(Consumer<Project> onOpenProject) {
        this.onOpenProject = onOpenProject;
        setLayout(new BorderLayout());
        setBackground(Color.WHITE);
        setBorder(BorderFactory.createEmptyBorder(24, 24, 24, 24));

        JLabel title = new JLabel("NEXT LEVEL CONSTRUCTION");
        title.setFont(title.getFont().deriveFont(Font.BOLD, 15f));
        title.setForeground(new Color(0x5B, 0x6B, 0x7A));
        add(title, BorderLayout.NORTH);

        grid.setBackground(Color.WHITE);
        grid.setBorder(BorderFactory.createEmptyBorder(20, 0, 0, 0));
        JPanel gridWrap = new JPanel(new FlowLayout(FlowLayout.LEFT));
        gridWrap.setBackground(Color.WHITE);
        gridWrap.add(grid);
        add(gridWrap, BorderLayout.CENTER);

        reload();
    }

    public void reload() {
        grid.removeAll();
        grid.add(newJobTile());
        for (Project p : projectDao.findAll()) grid.add(projectTile(p));
        grid.revalidate();
        grid.repaint();
    }

    private JPanel newJobTile() {
        JPanel cell = tileWrapper();
        CircleButton circle = new CircleButton("+", true);
        circle.addMouseListener(clickHandler(this::showNewJobDialog));
        JLabel label = tileLabel("New Job");
        cell.add(circle, BorderLayout.CENTER);
        cell.add(label, BorderLayout.SOUTH);
        return cell;
    }

    private JPanel projectTile(Project p) {
        JPanel cell = tileWrapper();
        CircleButton circle = new CircleButton(p.abbr);
        circle.addMouseListener(clickHandler(() -> onOpenProject.accept(p)));
        JLabel label = tileLabel(p.name);
        cell.add(circle, BorderLayout.CENTER);
        cell.add(label, BorderLayout.SOUTH);
        return cell;
    }

    private JPanel tileWrapper() {
        JPanel cell = new JPanel(new BorderLayout(0, 8));
        cell.setBackground(Color.WHITE);
        return cell;
    }

    private JLabel tileLabel(String text) {
        JLabel l = new JLabel(text, SwingConstants.CENTER);
        l.setFont(l.getFont().deriveFont(Font.BOLD, 11.5f));
        l.setForeground(new Color(0x10, 0x23, 0x3B));
        return l;
    }

    private java.awt.event.MouseAdapter clickHandler(Runnable r) {
        return new java.awt.event.MouseAdapter() {
            @Override public void mouseClicked(java.awt.event.MouseEvent e) { r.run(); }
        };
    }

    private void showNewJobDialog() {
        JTextField abbrField = new JTextField();
        JTextField nameField = new JTextField();
        JPanel form = new JPanel(new java.awt.GridLayout(0, 1, 4, 4));
        form.add(new JLabel("Abbreviation (2-5 letters, shows in the circle):"));
        form.add(abbrField);
        form.add(new JLabel("Job name:"));
        form.add(nameField);

        int result = JOptionPane.showConfirmDialog(this, form, "New Job",
                JOptionPane.OK_CANCEL_OPTION, JOptionPane.PLAIN_MESSAGE);
        if (result == JOptionPane.OK_OPTION) {
            String abbr = abbrField.getText().trim();
            String name = nameField.getText().trim();
            if (abbr.isEmpty() && name.isEmpty()) return;
            Project p = projectDao.create(abbr, name);
            reload();
            onOpenProject.accept(p);
        }
    }
}
