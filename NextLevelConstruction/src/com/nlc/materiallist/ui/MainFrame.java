package com.nlc.materiallist.ui;

import java.awt.BorderLayout;
import java.awt.CardLayout;
import java.awt.Color;
import java.awt.Font;
import java.awt.GridLayout;

import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.SwingConstants;
import javax.swing.border.EmptyBorder;

import com.nlc.materiallist.model.Project;

/**
 * Top-level window. Three-level navigation, same shape as the web app:
 *   Home (project circles) -> Project menu (Dashboard/Sub-Floor/DB/Suppliers circles) -> a screen
 * The back link in the top bar always goes up exactly one level.
 */
public class MainFrame extends JFrame {

    private static final Color INK = new Color(0x10, 0x23, 0x3B);
    private static final Color ORANGE = new Color(0xE2, 0x60, 0x0C);

    private final CardLayout cards = new CardLayout();
    private final JPanel cardHost = new JPanel(cards);
    private final JLabel backLink = new JLabel("");

    private Project currentProject;
    private String currentLevel = "home"; // home | project-menu | screen

    public MainFrame() {
        super("Next Level Construction — Material List");
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setSize(1180, 780);
        setLocationRelativeTo(null);
        setLayout(new BorderLayout());

        add(topBar(), BorderLayout.NORTH);
        add(cardHost, BorderLayout.CENTER);
        add(bottomNav(), BorderLayout.SOUTH);

        showHome();
    }

    private JPanel topBar() {
        JPanel bar = new JPanel(new BorderLayout());
        bar.setBackground(INK);
        bar.setBorder(new EmptyBorder(12, 18, 12, 18));

        JLabel brand = new JLabel("NEXT LEVEL CONSTRUCTION");
        brand.setForeground(Color.WHITE);
        brand.setFont(brand.getFont().deriveFont(Font.BOLD, 16f));

        backLink.setForeground(new Color(255, 255, 255, 210));
        backLink.setFont(backLink.getFont().deriveFont(Font.BOLD, 12.5f));
        backLink.setBorder(new EmptyBorder(0, 24, 0, 0));
        backLink.setCursor(new java.awt.Cursor(java.awt.Cursor.HAND_CURSOR));
        backLink.addMouseListener(new java.awt.event.MouseAdapter() {
            @Override public void mouseClicked(java.awt.event.MouseEvent e) { goBackOneLevel(); }
        });

        JPanel left = new JPanel(new java.awt.FlowLayout(java.awt.FlowLayout.LEFT));
        left.setBackground(INK);
        left.add(brand);
        left.add(backLink);
        bar.add(left, BorderLayout.WEST);
        return bar;
    }

    private JPanel bottomNav() {
        JPanel nav = new JPanel(new GridLayout(1, 3));
        nav.setBackground(INK);
        nav.add(navButton("Home", this::showHome));
        nav.add(navButton("Lista", this::showList));
        nav.add(navButton("More", this::showAbout));
        return nav;
    }

    private JButton navButton(String label, Runnable action) {
        JButton b = new JButton(label);
        b.setBackground(INK);
        b.setForeground(Color.WHITE);
        b.setFont(b.getFont().deriveFont(Font.BOLD, 12f));
        b.setBorder(new EmptyBorder(10, 4, 10, 4));
        b.setFocusPainted(false);
        b.setHorizontalAlignment(SwingConstants.CENTER);
        b.addActionListener(e -> action.run());
        return b;
    }

    // ---------------- navigation ----------------

    private HomePanel homePanel;

    public void showHome() {
        currentLevel = "home";
        currentProject = null;
        backLink.setText("");
        if (homePanel == null) {
            homePanel = new HomePanel(this::openProject);
            cardHost.add(homePanel, "home");
        } else {
            homePanel.reload();
        }
        cards.show(cardHost, "home");
    }

    private ProjectListPanel listPanel;

    /** Lista (All Jobs): rebuilt each time so new and renamed jobs show up. */
    public void showList() {
        currentLevel = "home";   // like Home: the back link has nothing above it
        currentProject = null;
        backLink.setText("");
        if (listPanel != null) cardHost.remove(listPanel);
        listPanel = new ProjectListPanel(this::openProject);
        cardHost.add(listPanel, "list");
        cards.show(cardHost, "list");
    }

    public void openProject(Project project) {
        currentProject = project;
        com.nlc.materiallist.service.AuditService.ensureBaseline(project.id);
        currentLevel = "project-menu";
        backLink.setText("\u2190 All Jobs");
        ProjectMenuPanel menu = new ProjectMenuPanel(project, this::openTile);
        cardHost.add(menu, "project-menu");
        cards.show(cardHost, "project-menu");
    }

    public void openTile(String tileId) {
        currentLevel = "screen";
        backLink.setText("\u2190 " + currentProject.name);
        JPanel screen;
        switch (tileId) {
            case "dashboard": screen = new DashboardPanel(currentProject); break;
            case "ordered": screen = new OrderedPanel(currentProject); break;
            case "received": screen = new ReceivedPanel(currentProject); break;
            case "audit": screen = new AuditPanel(currentProject); break;
            case "database": screen = new MaterialsDbPanel(currentProject); break;
            case "suppliers": screen = new SuppliersPanel(currentProject); break;
            default: screen = new SectionPanel(currentProject, tileId); break;
        }
        cardHost.add(screen, "screen");
        cards.show(cardHost, "screen");
    }

    private void goBackOneLevel() {
        if ("screen".equals(currentLevel)) {
            openProject(currentProject);
        } else if ("project-menu".equals(currentLevel)) {
            showHome();
        }
    }

    private void showAbout() {
        javax.swing.JOptionPane.showMessageDialog(this,
                "Next Level Construction — Material List\n\n" +
                "Cada job tem seu banco de dados local (SQLite) em:\n" +
                System.getProperty("user.home") + "/NextLevelConstruction/material_list.db\n\n" +
                "QTY calculado com a mesma fórmula da planilha original.",
                "More", javax.swing.JOptionPane.INFORMATION_MESSAGE);
    }
}
