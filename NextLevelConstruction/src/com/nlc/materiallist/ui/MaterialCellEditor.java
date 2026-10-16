package com.nlc.materiallist.ui;

import java.awt.Component;

import javax.swing.DefaultCellEditor;
import javax.swing.JComboBox;
import javax.swing.JTable;

import com.nlc.materiallist.data.SeedData;

/**
 * Material cell editor whose option list depends on the row's current Species value.
 * Rebuilt fresh every time the cell is opened for editing, so it's always in sync —
 * this is the Swing equivalent of the dependent dropdown from the web app, but without
 * the HTML "&lt;datalist&gt; inside &lt;tr&gt;" pitfall that caused it to silently break there.
 */
public class MaterialCellEditor extends DefaultCellEditor {

    private final JComboBox<String> combo;

    public MaterialCellEditor() {
        super(new JComboBox<>());
        combo = (JComboBox<String>) getComponent();
        combo.setEditable(true);
    }

    @Override
    public Component getTableCellEditorComponent(JTable table, Object value, boolean isSelected, int row, int column) {
        String species = String.valueOf(table.getModel().getValueAt(row, TakeoffTableModel.COL_SPECIES));
        combo.removeAllItems();
        for (String m : SeedData.materialsForSpecies(species)) combo.addItem(m);
        combo.setSelectedItem(value == null ? "" : value.toString());
        return combo;
    }
}
