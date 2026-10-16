package com.nlc.materiallist.ui;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Cursor;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;

import javax.swing.JComponent;

/**
 * A round tile button: dark filled circle with a short label inside, matching the
 * "job circle" / "section circle" look from the web app's Home and project-menu screens.
 * Dashed style is used for the "+ New Job" tile.
 */
public class CircleButton extends JComponent {

    private String text;
    private boolean dashed;
    private boolean hover = false;
    private static final Color INK = new Color(0x10, 0x23, 0x3B);
    private static final Color ORANGE = new Color(0xE2, 0x60, 0x0C);
    private static final Color LINE = new Color(0xC7, 0xD2, 0xDB);

    public CircleButton(String text) { this(text, false); }

    public CircleButton(String text, boolean dashed) {
        this.text = text;
        this.dashed = dashed;
        setPreferredSize(new Dimension(104, 104));
        setCursor(new Cursor(Cursor.HAND_CURSOR));
        addMouseListener(new MouseAdapter() {
            @Override public void mouseEntered(MouseEvent e) { hover = true; repaint(); }
            @Override public void mouseExited(MouseEvent e) { hover = false; repaint(); }
        });
    }

    public void setText(String text) { this.text = text; repaint(); }

    @Override
    protected void paintComponent(Graphics g) {
        Graphics2D g2 = (Graphics2D) g.create();
        g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        int d = Math.min(getWidth(), getHeight()) - (hover ? 6 : 2);
        int x = (getWidth() - d) / 2;
        int y = (getHeight() - d) / 2 + (hover ? 0 : 2);

        if (dashed) {
            g2.setColor(hover ? new Color(0xEA, 0xF1, 0xF8) : getBackground());
            g2.fillOval(x, y, d, d);
            g2.setStroke(new BasicStroke(2f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND, 1f, new float[]{6f, 5f}, 0f));
            g2.setColor(hover ? ORANGE : LINE);
            g2.drawOval(x, y, d - 2, d - 2);
            g2.setColor(ORANGE);
            g2.setFont(getFont().deriveFont(Font.PLAIN, d * 0.34f));
            drawCentered(g2, "+", x, y, d, d);
        } else {
            g2.setColor(INK);
            g2.fillOval(x, y, d, d);
            g2.setColor(Color.WHITE);
            g2.setFont(getFont().deriveFont(Font.BOLD, Math.max(11f, d * 0.17f)));
            drawWrapped(g2, text, x, y, d, d);
        }
        g2.dispose();
    }

    private void drawCentered(Graphics2D g2, String s, int x, int y, int w, int h) {
        var fm = g2.getFontMetrics();
        int tx = x + (w - fm.stringWidth(s)) / 2;
        int ty = y + (h - fm.getHeight()) / 2 + fm.getAscent();
        g2.drawString(s, tx, ty);
    }

    /** Wraps to a second line on a space if the label is too wide for the circle. */
    private void drawWrapped(Graphics2D g2, String s, int x, int y, int w, int h) {
        var fm = g2.getFontMetrics();
        int maxWidth = (int) (w * 0.78);
        if (fm.stringWidth(s) <= maxWidth || !s.contains(" ")) {
            drawCentered(g2, s, x, y, w, h);
            return;
        }
        int mid = s.indexOf(' ', s.length() / 2 - 2);
        if (mid < 0) mid = s.indexOf(' ');
        String l1 = s.substring(0, mid), l2 = s.substring(mid + 1);
        int lh = fm.getHeight();
        int tx1 = x + (w - fm.stringWidth(l1)) / 2;
        int tx2 = x + (w - fm.stringWidth(l2)) / 2;
        int ty1 = y + h / 2 - 2;
        g2.drawString(l1, tx1, ty1);
        g2.drawString(l2, tx2, ty1 + lh);
    }

    @Override
    public Dimension getPreferredSize() { return new Dimension(104, 104); }
}
