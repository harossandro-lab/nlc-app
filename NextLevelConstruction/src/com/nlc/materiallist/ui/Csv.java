package com.nlc.materiallist.ui;

import java.awt.Component;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

import javax.swing.JFileChooser;
import javax.swing.JOptionPane;

/** CSV helpers shared by the Export CSV buttons. */
final class Csv {

    private Csv() {}

    /** Quotes a cell when it contains a comma, a quote or a line break. */
    static String cell(String v) {
        if (v == null) return "";
        if (v.contains(",") || v.contains("\"") || v.contains("\n")) return "\"" + v.replace("\"", "\"\"") + "\"";
        return v;
    }

    static void appendRow(StringBuilder sb, String... cells) {
        for (int i = 0; i < cells.length; i++) {
            if (i > 0) sb.append(',');
            sb.append(cell(cells[i]));
        }
        sb.append('\n');
    }

    /** Asks where to save and writes the file (UTF-8). */
    static void saveWithDialog(Component parent, String suggestedName, String content) {
        JFileChooser chooser = new JFileChooser();
        chooser.setSelectedFile(new File(suggestedName));
        if (chooser.showSaveDialog(parent) != JFileChooser.APPROVE_OPTION) return;
        try {
            Files.write(chooser.getSelectedFile().toPath(), content.getBytes(StandardCharsets.UTF_8));
        } catch (IOException ex) {
            JOptionPane.showMessageDialog(parent, "Não consegui salvar o arquivo: " + ex.getMessage(), "Export CSV", JOptionPane.ERROR_MESSAGE);
        }
    }
}
