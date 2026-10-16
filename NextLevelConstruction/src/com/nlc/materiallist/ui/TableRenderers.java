package com.nlc.materiallist.ui;

import java.awt.Color;
import java.awt.Component;
import java.awt.Font;

import javax.swing.JLabel;
import javax.swing.JTable;
import javax.swing.SwingConstants;
import javax.swing.border.EmptyBorder;
import javax.swing.table.DefaultTableCellRenderer;

public class TableRenderers {

    private TableRenderers() {}

    public static class StatusRenderer extends DefaultTableCellRenderer {
        public StatusRenderer() { setHorizontalAlignment(SwingConstants.CENTER); setOpaque(true); setBorder(new EmptyBorder(2, 6, 2, 6)); }
        @Override
        public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int col) {
            super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, col);
            String status = String.valueOf(value);
            setFont(getFont().deriveFont(Font.BOLD, 11f));
            setText(cap(status));
            if ("ordered".equals(status)) { setBackground(new Color(0xFB, 0xF0, 0xDC)); setForeground(new Color(0xB9, 0x79, 0x0E)); }
            else if ("received".equals(status)) { setBackground(new Color(0xE7, 0xF3, 0xEC)); setForeground(new Color(0x2F, 0x7A, 0x4D)); }
            else { setBackground(new Color(0xF1, 0xF3, 0xF5)); setForeground(new Color(0x5B, 0x6B, 0x7A)); }
            return this;
        }
        private String cap(String s) { return s.isEmpty() ? s : Character.toUpperCase(s.charAt(0)) + s.substring(1); }
    }

    public static class DeleteRenderer extends DefaultTableCellRenderer {
        public DeleteRenderer() { setHorizontalAlignment(SwingConstants.CENTER); }
        @Override
        public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int col) {
            JLabel l = (JLabel) super.getTableCellRendererComponent(table, "×", isSelected, hasFocus, row, col);
            l.setForeground(new Color(0xB2, 0x3A, 0x2E));
            l.setFont(l.getFont().deriveFont(Font.BOLD, 14f));
            return l;
        }
    }

    public static class ComputedRenderer extends DefaultTableCellRenderer {
        public ComputedRenderer() { setHorizontalAlignment(SwingConstants.RIGHT); }
        @Override
        public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int col) {
            super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, col);
            setForeground(new Color(0x5B, 0x6B, 0x7A));
            setFont(new Font(Font.MONOSPACED, Font.PLAIN, 12));
            return this;
        }
    }
}
