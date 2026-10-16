package com.nlc.materiallist.calc;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.nlc.materiallist.model.MaterialDbEntry;
import com.nlc.materiallist.model.ReceivedEntry;
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

    // ---------------------------------------------------------------
    // Ordered (auto) — replaces the manual TAKEOFF sheet + Update_ORDERED_All:
    // sum of QTY by GROUP -> ItemKey across all sections (same as aggregateByGroup in the web app).
    // ---------------------------------------------------------------
    public static final String NO_GROUP = "(sem grupo)";

    /** One consolidated line: the first take-off line seen for the key supplies material/length/species/price. */
    public static final class OrderedLine {
        public String material, length, species;
        public int qty;
        public Double unit;     // unit price with tax; null when the key is not in the Materials DB
        public String supply;   // null when the key is not in the Materials DB
        public Double total() { return unit == null ? null : unit * qty; }
    }

    /**
     * Group name -> (lower-case ItemKey -> line), both in first-seen order. Pass the items in workbook
     * section order. Lines with an empty ItemKey or without a QTY are skipped; a blank GROUP becomes NO_GROUP.
     */
    public static Map<String, Map<String, OrderedLine>> aggregateByGroup(
            List<TakeoffItem> items, List<MaterialDbEntry> database, List<Supplier> suppliers) {
        Map<String, Map<String, OrderedLine>> byGroup = new LinkedHashMap<>();
        for (TakeoffItem it : items) {
            String g = (it.group == null || it.group.isEmpty()) ? NO_GROUP : it.group;
            String k = itemKeyOf(it);
            if (k.isEmpty()) continue;
            Integer qty = computeQty(it);
            if (qty == null || qty == 0) continue;
            MaterialDbEntry db = findDbEntry(it, database);
            Map<String, OrderedLine> lines = byGroup.computeIfAbsent(g, x -> new LinkedHashMap<>());
            OrderedLine line = lines.get(k);
            if (line == null) {
                line = new OrderedLine();
                line.material = it.material; line.length = it.length; line.species = it.species;
                line.unit = db == null ? null : unitPriceOf(db, suppliers);
                line.supply = db == null ? null : db.supply;
                lines.put(k, line);
            }
            line.qty += qty;
        }
        return byGroup;
    }

    // ---------------------------------------------------------------
    // Received — delivery log, compared with Ordered by GROUP (same rules as the web app's Received tab)
    // ---------------------------------------------------------------

    /** Price of a delivered line = Materials DB unit price (with tax) * qty, or null when the key is not in the DB. */
    public static Double receivedLineTotal(ReceivedEntry r, List<MaterialDbEntry> database, List<Supplier> suppliers) {
        TakeoffItem key = new TakeoffItem();
        key.material = r.material; key.length = r.length; key.species = r.species;
        MaterialDbEntry db = findDbEntry(key, database);
        Double unit = db == null ? null : unitPriceOf(db, suppliers);
        double qty = r.qty == null ? 0 : r.qty;
        return unit == null ? null : unit * qty;
    }

    /** Ordered value of one group: sum of unit price * qty over the lines that have a price. */
    public static double orderedTotal(Map<String, OrderedLine> lines) {
        double sum = 0;
        for (OrderedLine l : lines.values()) if (l.unit != null) sum += l.unit * l.qty;
        return sum;
    }

    /** Delivered value of one group: sum of the priced deliveries whose GROUP is exactly this one. */
    public static double deliveredTotal(String group, List<ReceivedEntry> received,
                                        List<MaterialDbEntry> database, List<Supplier> suppliers) {
        double sum = 0;
        for (ReceivedEntry r : received) {
            if (!group.equals(r.group)) continue;
            Double t = receivedLineTotal(r, database, suppliers);
            if (t != null) sum += t;
        }
        return sum;
    }

    /** Delivered as a percentage of ordered, capped at 100 (0 when nothing was ordered). */
    public static double deliveredPercent(double delivered, double ordered) {
        return ordered != 0 ? Math.min(100, delivered / ordered * 100) : 0;
    }

    /**
     * Two decimals the way JavaScript's toFixed(2) does it: rounded from the exact binary value of the double
     * (half up), not from its shortest decimal text — so 10.825 gives "10.82" here and in the web app.
     */
    public static String fixed2(double v) {
        return new BigDecimal(v).setScale(2, RoundingMode.HALF_UP).toPlainString();
    }

    /** Money like the web app's money(): "$1,234.50" (US format, same exact rounding as fixed2). */
    public static String money(double v) {
        BigDecimal r = new BigDecimal(v).setScale(2, RoundingMode.HALF_UP);
        return "$" + new DecimalFormat("#,##0.00", DecimalFormatSymbols.getInstance(Locale.US)).format(r);
    }

    /** Display order of the groups: the canonical GROUP list first, then any other group found. */
    public static List<String> groupDisplayOrder(Collection<String> present, List<String> canonical) {
        List<String> out = new ArrayList<>();
        for (String g : canonical) if (present.contains(g)) out.add(g);
        for (String g : present) if (!canonical.contains(g)) out.add(g);
        return out;
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
