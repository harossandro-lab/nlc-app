package com.nlc.materiallist.ui;

import java.util.List;

import javax.swing.DefaultCellEditor;
import javax.swing.JComboBox;

/** A combo-box cell editor backed by a fixed list of suggestions (Group, Length, Species, SP, Location...). */
public class SuggestCellEditor extends DefaultCellEditor {

    public SuggestCellEditor(List<String> options, boolean editable) {
        super(buildCombo(options, editable));
    }

    private static JComboBox<String> buildCombo(List<String> options, boolean editable) {
        JComboBox<String> combo = new JComboBox<>();
        combo.addItem(""); // blank option so a field can start unset
        for (String o : options) combo.addItem(o);
        combo.setEditable(editable);
        return combo;
    }
}
