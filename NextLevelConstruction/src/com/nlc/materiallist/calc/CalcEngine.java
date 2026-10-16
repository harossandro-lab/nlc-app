package com.nlc.materiallist.calc;

import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.nlc.materiallist.model.MaterialDbEntry;
import com.nlc.materiallist.model.Supplier;
import com.nlc.materiallist.model.TakeoffItem;

/**
 * Faithful port of the original workbook's native LET() QTY formula (identical on every
 * take-off tab of the source spreadsheet), the BuildItemKey() logic from the workbook's
 * VBA modules, and the Unit Price = Out-Tax-Price * (1 + Supplier Tax%) pricing rule.
 *
 * This is the one file that encodes the actual business logic of the tool — keep it in
 * sync with CalcEngine's counterpart in the web app if you change either.
 */
public final class CalcEngine {

    private CalcEngine() {}

    // ---------------------------------------------------------------
    // LENGTH parsing — mirrors:
    //   VALUE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(G,"'",""),'"',""),"SF",""))
    // Also understands mixed fractions like 104 5/8" since the workbook uses them
    // for dimensional lumber lengths (Excel's VALUE() only manages this loosely;
    // we do it properly here).
    // ---------------------------------------------------------------
    private static final Pattern MIXED_FRACTION = Pattern.compile("^(\\d+(?:\\.\\d+)?)\\s+(\\d+)/(\\d+)$");
    private static final Pattern PLAIN_FRACTION = Pattern.compile("^(\\d+)/(\\d+)$");

    public static Double parseLength(String raw) {
        if (raw == null) return null;
        String s = raw.trim();
        if (s.isEmpty() || s.equalsIgnoreCase("N/A")) return null;
        s = s.replace("'", "").replace("\"", "").replaceAll("(?i)SF", "").trim();
        if (s.isEmpty()) return null;
        Matcher m = MIXED_FRACTION.matcher(s);
        if (m.matches()) {
            return Double.parseDouble(m.group(1)) + Double.parseDouble(m.group(2)) / Double.parseDouble(m.group(3));
        }
        m = PLAIN_FRACTION.matcher(s);
        if (m.matches()) {
            return Double.parseDouble(m.group(1)) / Double.parseDouble(m.group(2));
        }
        try {
            return Double.parseDouble(s);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    /** Result of parsing the SP (spacing) column: either a spacing-in-inches, or a ply count, never both. */
    public static final class SpacingPly {
        public Double spacing; // inches
        public Double ply;
    }

    private static final Pattern PLY = Pattern.compile("(?i)(\\d+(?:\\.\\d+)?)\\s*ply");
    private static final Pattern FEET = Pattern.compile("(\\d+(?:\\.\\d+)?)\\s*'");
    private static final Pattern FEET_WORD = Pattern.compile("(?i)(\\d+(?:\\.\\d+)?)\\s*ft");
    private static final Pattern INCHES = Pattern.compile("(\\d+(?:\\.\\d+)?)\\s*\"");
    private static final Pattern INCHES_WORD = Pattern.compile("(?i)(\\d+(?:\\.\\d+)?)\\s*in");
    private static final Pattern NUMERIC = Pattern.compile("^\\d+(\\.\\d+)?$");

    public static SpacingPly parseSpacingAndPly(String spRaw) {
        SpacingPly out = new SpacingPly();
        if (spRaw == null || spRaw.trim().isEmpty()) return out;
        String spText = spRaw.trim();
        if (NUMERIC.matcher(spText).matches()) {
            out.spacing = Double.parseDouble(spText);
            return out;
        }
        Matcher m = PLY.matcher(spText);
        if (m.find()) { out.ply = Double.parseDouble(m.group(1)); return out; }
        m = FEET.matcher(spText);
        if (!m.find()) m = FEET_WORD.matcher(spText);
        if (m.find() || m.reset().find()) { /* handled below */ }
        Matcher mf = FEET.matcher(spText);
        if (mf.find()) { out.spacing = Double.parseDouble(mf.group(1)) * 12.0; return out; }
        Matcher mfw = FEET_WORD.matcher(spText);
        if (mfw.find()) { out.spacing = Double.parseDouble(mfw.group(1)) * 12.0; return out; }
        Matcher mi = INCHES.matcher(spText);
        if (mi.find()) { out.spacing = Double.parseDouble(mi.group(1)); return out; }
        Matcher miw = INCHES_WORD.matcher(spText);
        if (miw.find()) { out.spacing = Double.parseDouble(miw.group(1)); return out; }
        return out;
    }

    /**
     * The exact QTY formula from the workbook (LET() on every take-off sheet):
     *  - "End Stud" purpose  -> LF * 2 / 12
     *  - spacing present     -> (LF*12/spacing) [* EA if EA also given]
     *  - "N Ply" in SP       -> ply*LF/length, or ply*EA
     *  - otherwise           -> LF/length, or SF/length, or EA directly
     *  - +5% waste if purpose contains both "sheathing" and "roof"
     *  - rounded UP to the nearest whole piece (CEILING.MATH)
     * Returns null when there isn't enough information to compute a quantity.
     */
    public static Integer computeQty(TakeoffItem it) {
        Double len = parseLength(it.length);
        double lf = it.lf == null ? 0 : it.lf;
        double sf = it.sf == null ? 0 : it.sf;
        double ea = it.ea == null ? 0 : it.ea;
        String desc = it.purpose == null ? "" : it.purpose.toLowerCase();
        SpacingPly sap = parseSpacingAndPly(it.sp);
        Double spacing = sap.spacing, ply = sap.ply;
        Double spacingCount = (spacing != null && spacing > 0 && lf > 0) ? (lf * 12.0 / spacing) : null;

        Double rawQty = null;
        if (desc.contains("end stud")) {
            rawQty = lf > 0 ? (lf * 2.0 / 12.0) : null;
        } else if (spacingCount != null && spacingCount > 0 && ea > 0) {
            rawQty = spacingCount * ea;
        } else if (spacingCount != null && spacingCount > 0) {
            rawQty = spacingCount;
        } else if (ply != null && ply > 0 && lf > 0 && len != null) {
            rawQty = (ply * lf) / len;
        } else if (ply != null && ply > 0 && ea > 0) {
            rawQty = ply * ea;
        } else if (lf > 0 && len != null) {
            rawQty = lf / len;
        } else if (sf > 0 && len != null) {
            rawQty = sf / len;
        } else if (ea > 0) {
            rawQty = ea;
        }
        if (rawQty == null) return null;

        double addWaste = (desc.contains("sheathing") && desc.contains("roof")) ? 1.05 : 1.0;
        return (int) Math.ceil(rawQty * addWaste);
    }

    // ---------------------------------------------------------------
    // ItemKey — mirrors BuildItemKey() from the workbook's VBA (Module2.bas):
    // MATERIAL|LENGTH|SPECIES, blank/"N/A" length dropped, parts joined with "|".
    // ---------------------------------------------------------------
    private static String cleanKeyPart(String v) { return v == null ? "" : v.trim(); }

    public static String buildItemKey(String material, String length, String species) {
        String p0 = cleanKeyPart(material);
        String p1 = cleanKeyPart(length);
        String p2 = cleanKeyPart(species);
        if (p1.equalsIgnoreCase("N/A")) p1 = "";
        StringBuilder sb = new StringBuilder();
        if (!p0.isEmpty()) sb.append(p0);
        if (!p1.isEmpty()) { if (sb.length() > 0) sb.append('|'); sb.append(p1); }
        if (!p2.isEmpty()) { if (sb.length() > 0) sb.append('|'); sb.append(p2); }
        return sb.toString();
    }

    public static String itemKeyOf(TakeoffItem it) {
        return buildItemKey(it.material, it.length, it.species).toLowerCase();
    }

    public static String dbKeyOf(MaterialDbEntry d) {
        return buildItemKey(d.material, d.length, d.species).toLowerCase();
    }

    // ---------------------------------------------------------------
    // Pricing: Unit Price = Out-Tax-Price * (1 + Supplier Tax%)
    // ---------------------------------------------------------------
    public static double taxForSupply(List<Supplier> suppliers, String supplyName) {
        if (supplyName == null) return 0;
        for (Supplier s : suppliers) {
            if (s.name != null && s.name.trim().equalsIgnoreCase(supplyName.trim())) return s.tax;
        }
        return 0;
    }

    public static MaterialDbEntry findDbEntry(TakeoffItem it, List<MaterialDbEntry> database) {
        String k = itemKeyOf(it);
        if (k.isEmpty()) return null;
        for (MaterialDbEntry d : database) {
            if (dbKeyOf(d).equals(k)) return d;
        }
        return null;
    }

    public static Double unitPriceOf(MaterialDbEntry d, List<Supplier> suppliers) {
        if (d == null) return null;
        return d.unitPriceOutTax * (1 + taxForSupply(suppliers, d.supply) / 100.0);
    }

    /** Line total = QTY * Unit Price (with tax), or null if either is unavailable. */
    public static Double lineTotal(TakeoffItem it, List<MaterialDbEntry> database, List<Supplier> suppliers) {
        MaterialDbEntry db = findDbEntry(it, database);
        if (db == null) return null;
        Integer qty = computeQty(it);
        if (qty == null) return null;
        Double unit = unitPriceOf(db, suppliers);
        return unit == null ? null : unit * qty;
    }
}
