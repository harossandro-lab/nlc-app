package com.nlc.materiallist.ui;

import java.util.List;

import javax.swing.table.AbstractTableModel;

import com.nlc.materiallist.calc.CalcEngine;
import com.nlc.materiallist.dao.MaterialDbDao;
import com.nlc.materiallist.dao.SupplierDao;
import com.nlc.materiallist.dao.TakeoffItemDao;
import com.nlc.materiallist.service.AuditService;
import com.nlc.materiallist.model.MaterialDbEntry;
import com.nlc.materiallist.model.Supplier;
import com.nlc.materiallist.model.TakeoffItem;

/**
 * Table model for one take-off section. Every edited cell is written straight to SQLite
 * (via TakeoffItemDao) the moment it changes — there is no separate "save" step, matching
 * the always-synced feel of the web app.
 */
public class TakeoffTableModel extends AbstractTableModel {

    public static final int COL_GROUP = 0, COL_PURPOSE = 1, COL_DETAIL = 2, COL_MATERIAL = 3,
            COL_LENGTH = 4, COL_SPECIES = 5, COL_LF = 6, COL_SF = 7, COL_SP = 8, COL_EA = 9,
            COL_QTY = 10, COL_LOCATION = 11, COL_UNIT = 12, COL_TOTAL = 13, COL_STATUS = 14, COL_DELETE = 15;

    private static final String[] COLUMNS = {
            "Group", "Purpose", "Page/Detail", "Material", "Length", "Species",
            "LF", "SF", "SP", "EA", "QTY", "Location", "Unit $", "Total", "Status", ""
    };

    private final List<TakeoffItem> items;
    private final TakeoffItemDao itemDao;
    private final MaterialDbDao materialDao;
    private final SupplierDao supplierDao;
    private final String projectId;
    private final String sectionId;

    private List<MaterialDbEntry> databaseCache;
    private List<Supplier> suppliersCache;

    public TakeoffTableModel(String projectId, String sectionId, List<TakeoffItem> items,
                              TakeoffItemDao itemDao, MaterialDbDao materialDao, SupplierDao supplierDao) {
        this.projectId = projectId;
        this.sectionId = sectionId;
        this.items = items;
        this.itemDao = itemDao;
        this.materialDao = materialDao;
        this.supplierDao = supplierDao;
        refreshPricingCache();
    }

    /** Call after materials/suppliers change elsewhere so prices in this table stay correct. */
    public void refreshPricingCache() {
        databaseCache = materialDao.findByProject(projectId);
        suppliersCache = supplierDao.findByProject(projectId);
    }

    public TakeoffItem itemAt(int row) { return items.get(row); }

    /** Inserts a new blank row (with the section's default GROUP pre-filled) and appends it to the table. */
    public void addRow(String defaultGroup) {
        TakeoffItem it = new TakeoffItem();
        it.projectId = projectId;
        it.sectionId = sectionId;
        it.group = defaultGroup == null ? "" : defaultGroup;
        it.location = "FACTORY";
        it.status = "pending";
        itemDao.insert(it);
        items.add(it);
        fireTableRowsInserted(items.size() - 1, items.size() - 1);
        AuditService.schedule(projectId);
    }

    public void removeRow(int row) {
        TakeoffItem it = items.remove(row);
        itemDao.delete(it.id);
        fireTableRowsDeleted(row, row);
        AuditService.schedule(projectId);
    }

    public void cycleStatus(int row) {
        TakeoffItem it = items.get(row);
        String[] order = {"pending", "ordered", "received"};
        int idx = 0;
        for (int i = 0; i < order.length; i++) if (order[i].equals(it.status)) idx = i;
        it.status = order[(idx + 1) % order.length];
        itemDao.update(it);
        fireTableRowsUpdated(row, row);
    }

    public double sectionTotal() {
        double total = 0;
        for (TakeoffItem it : items) {
            Double t = CalcEngine.lineTotal(it, databaseCache, suppliersCache);
            if (t != null) total += t;
        }
        return total;
    }

    @Override public int getRowCount() { return items.size(); }
    @Override public int getColumnCount() { return COLUMNS.length; }
    @Override public String getColumnName(int col) { return COLUMNS[col]; }

    @Override
    public boolean isCellEditable(int row, int col) {
        return col != COL_QTY && col != COL_UNIT && col != COL_TOTAL && col != COL_STATUS && col != COL_DELETE;
    }

    @Override
    public Object getValueAt(int row, int col) {
        TakeoffItem it = items.get(row);
        switch (col) {
            case COL_GROUP: return it.group;
            case COL_PURPOSE: return it.purpose;
            case COL_DETAIL: return it.pageDetail;
            case COL_MATERIAL: return it.material;
            case COL_LENGTH: return it.length;
            case COL_SPECIES: return it.species;
            case COL_LF: return it.lf == null ? "" : fmtNum(it.lf);
            case COL_SF: return it.sf == null ? "" : fmtNum(it.sf);
            case COL_SP: return it.sp;
            case COL_EA: return it.ea == null ? "" : fmtNum(it.ea);
            case COL_QTY: {
                Integer q = CalcEngine.computeQty(it);
                return q == null ? "—" : String.valueOf(q);
            }
            case COL_LOCATION: return it.location;
            case COL_UNIT: {
                MaterialDbEntry db = CalcEngine.findDbEntry(it, databaseCache);
                Double u = CalcEngine.unitPriceOf(db, suppliersCache);
                return u == null ? "—" : String.format("%.2f", u);
            }
            case COL_TOTAL: {
                Double t = CalcEngine.lineTotal(it, databaseCache, suppliersCache);
                return t == null ? "—" : String.format("$%,.2f", t);
            }
            case COL_STATUS: return it.status == null ? "pending" : it.status;
            case COL_DELETE: return "×";
            default: return "";
        }
    }

    @Override
    public void setValueAt(Object value, int row, int col) {
        TakeoffItem it = items.get(row);
        String s = value == null ? "" : value.toString();
        switch (col) {
            case COL_GROUP: it.group = s; break;
            case COL_PURPOSE: it.purpose = s; break;
            case COL_DETAIL: it.pageDetail = s; break;
            case COL_MATERIAL: it.material = s; break;
            case COL_LENGTH: it.length = s; break;
            case COL_SPECIES: it.species = s; break;
            case COL_LF: it.lf = parseNum(s); break;
            case COL_SF: it.sf = parseNum(s); break;
            case COL_SP: it.sp = s; break;
            case COL_EA: it.ea = parseNum(s); break;
            case COL_LOCATION: it.location = s; break;
            default: return;
        }
        itemDao.update(it);
        fireTableRowsUpdated(row, row); // also refreshes the computed QTY/Unit/Total cells on this row
        AuditService.schedule(projectId);
    }

    private static Double parseNum(String s) {
        if (s == null || s.trim().isEmpty()) return null;
        try { return Double.parseDouble(s.trim().replace(",", ".")); } catch (NumberFormatException e) { return null; }
    }
    private static String fmtNum(double d) {
        return (d == Math.floor(d)) ? String.valueOf((long) d) : String.valueOf(d);
    }
}
