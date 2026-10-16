/*
 * Regression check for the business logic (CalcEngine QTY / ItemKey / price rules), the seed lists
 * and the SQLite schema. No GUI needed.
 *
 * Run it with a throwaway user.home so the real database (~/NextLevelConstruction) is not touched.
 * Expected last line: RESULT pass=36 fail=0   (exact commands are in CLAUDE.md)
 */
import com.nlc.materiallist.calc.CalcEngine;
import com.nlc.materiallist.data.SeedData;
import com.nlc.materiallist.db.Database;
import com.nlc.materiallist.model.MaterialDbEntry;
import com.nlc.materiallist.model.Supplier;
import com.nlc.materiallist.model.TakeoffItem;
import java.nio.file.*;
import java.sql.*;
import java.util.*;

public class SmokeCheck {
    static int pass = 0, fail = 0;
    static void check(String name, Object got, Object want) {
        boolean ok = Objects.equals(got, want);
        if (ok) pass++; else fail++;
        System.out.println((ok ? "PASS  " : "FAIL  ") + name + "  got=" + got + "  want=" + want);
    }
    static TakeoffItem it(String purpose, String length, Double lf, Double sf, String sp, Double ea) {
        TakeoffItem t = new TakeoffItem();
        t.purpose = purpose; t.length = length; t.lf = lf; t.sf = sf; t.sp = sp; t.ea = ea;
        return t;
    }
    public static void main(String[] args) throws Exception {
        // reference data
        check("GROUPS count", SeedData.GROUPS.size(), 43);
        check("GROUPS keeps original typo", SeedData.GROUPS.contains("SUB-LOOR - WALL"), true);
        check("GROUPS keeps double space", SeedData.GROUPS.contains("BALCONY - FRONT  ELEVATION"), true);
        check("SECTIONS count", SeedData.SECTIONS.size(), 13);
        check("SPECIES count", SeedData.SPECIES.size(), 25);
        check("SPACINGS has 8 feet (8')", SeedData.SPACINGS.contains("8'"), true);
        check("SPACINGS has 8 inches (8\")", SeedData.SPACINGS.contains("8\""), true);
        check("DF.No2 materials", SeedData.materialsForSpecies("DF.No2").size(), 7);
        check("LVL materials", SeedData.materialsForSpecies("LVL").size(), 90);
        // QTY rules
        check("LF/length (100/8=12.5 -> 13)", CalcEngine.computeQty(it("Stud", "8'", 100.0, null, "", null)), 13);
        check("spacing 16in (100*12/16=75)", CalcEngine.computeQty(it("Stud", "8'", 100.0, null, "16\"", null)), 75);
        check("spacing x EA (7.5*2=15)", CalcEngine.computeQty(it("Stud", "8'", 10.0, null, "16\"", 2.0)), 15);
        check("end stud (100*2/12=16.7 -> 17)", CalcEngine.computeQty(it("End Studs", "8'", 100.0, null, "", null)), 17);
        check("2 Ply with LF (2*30/16=3.75 -> 4)", CalcEngine.computeQty(it("Header", "16'", 30.0, null, "2 Ply", null)), 4);
        check("3 Ply with EA (3*3=9)", CalcEngine.computeQty(it("Header", "", null, null, "3 Ply", 3.0)), 9);
        check("SF/length (650/32=20.3 -> 21)", CalcEngine.computeQty(it("Floor Sheathing", "32SF", null, 650.0, "", null)), 21);
        check("roof sheathing +5% (20.3125*1.05 -> 22)", CalcEngine.computeQty(it("Roof Sheathing", "32SF", null, 650.0, "", null)), 22);
        check("EA only", CalcEngine.computeQty(it("Hanger", "", null, null, "", 7.0)), 7);
        check("not enough data -> null", CalcEngine.computeQty(it("Stud", "N/A", 10.0, null, "", null)), null);
        // length parsing
        check("parseLength 104 5/8\"", CalcEngine.parseLength("104 5/8\""), 104.625);
        check("parseLength N/A", CalcEngine.parseLength("N/A"), null);
        check("parseLength 32SF", CalcEngine.parseLength("32SF"), 32.0);
        check("parseLength 10'", CalcEngine.parseLength("10'"), 10.0);
        // ItemKey
        check("ItemKey full", CalcEngine.buildItemKey("2X4", "12'", "DF.No2"), "2X4|12'|DF.No2");
        check("ItemKey N/A length dropped", CalcEngine.buildItemKey("HANGER", "N/A", "HANGERS_CLIPS"), "HANGER|HANGERS_CLIPS");
        TakeoffItem k = it("x", "12'", null, null, "", null); k.material = "2X4"; k.species = "DF.No2";
        check("itemKeyOf is lowercase", CalcEngine.itemKeyOf(k), "2x4|12'|df.no2");
        // price
        MaterialDbEntry d = new MaterialDbEntry(); d.unitPriceOutTax = 10.0; d.supply = "ACME";
        Supplier s = new Supplier(); s.name = "acme"; s.tax = 8.25;
        double unit = CalcEngine.unitPriceOf(d, Arrays.asList(s));
        check("unit price = 10 * (1 + 8.25%)", Math.abs(unit - 10.825) < 1e-9, true);
        // database + schema.sql from classpath
        Connection c = Database.get();
        Set<String> tables = new TreeSet<>();
        try (Statement st = c.createStatement(); ResultSet rs = st.executeQuery("SELECT name FROM sqlite_master WHERE type='table'")) {
            while (rs.next()) tables.add(rs.getString(1));
        }
        for (String t : new String[]{"projects", "project_info", "suppliers", "materials_db", "takeoff_items"})
            check("table exists: " + t, tables.contains(t), true);
        // Project menu: Dashboard + 13 sections (workbook order) + Materials DB + Suppliers & Tax
        List<String> tileIds = new ArrayList<>(com.nlc.materiallist.ui.ProjectMenuPanel.TILES.keySet());
        List<String> wantTiles = new ArrayList<>();
        wantTiles.add("dashboard");
        for (SeedData.Section sec : SeedData.SECTIONS) wantTiles.add(sec.id);
        wantTiles.add("ordered"); wantTiles.add("database"); wantTiles.add("suppliers");
        check("menu tiles = dashboard + 13 sections + ordered + db + suppliers", tileIds, wantTiles);
        check("menu tile count", tileIds.size(), 17);
        System.setProperty("java.awt.headless", "true");
        com.nlc.materiallist.model.Project proj = new com.nlc.materiallist.dao.ProjectDao().create("TST", "Smoke");
        new com.nlc.materiallist.ui.ProjectMenuPanel(proj, id -> {});
        int built = 0;
        for (SeedData.Section sec : SeedData.SECTIONS) {
            new com.nlc.materiallist.ui.SectionPanel(proj, sec.id);
            built++;
        }
        check("SectionPanel builds for every section", built, 13);
        com.nlc.materiallist.dao.TakeoffItemDao itemDao = new com.nlc.materiallist.dao.TakeoffItemDao();
        TakeoffItem saved = it("Stud", "12'", 24.0, null, "", null);
        saved.projectId = proj.id; saved.sectionId = "roof"; saved.material = "2X4"; saved.species = "DF.No2"; saved.group = "ROOF";
        itemDao.insert(saved);
        check("OrderedPanel builds from the database", new com.nlc.materiallist.ui.OrderedPanel(proj) != null, true);
        // Ordered (auto): sum of QTY by GROUP -> ItemKey
        String g1 = "1ST FLOOR - WALL";
        TakeoffItem o1 = it("Stud", "12'", 24.0, null, "", null); o1.material = "2X4"; o1.species = "DF.No2"; o1.group = g1;  // 24/12 = 2
        TakeoffItem o2 = it("Stud", "12'", 36.0, null, "", null); o2.material = "2X4"; o2.species = "DF.No2"; o2.group = g1;  // 36/12 = 3
        TakeoffItem o3 = it("Hanger", "", null, null, "", 4.0);   o3.material = "HANGER"; o3.species = "HANGERS_CLIPS"; o3.group = "";  // no group, not in DB
        TakeoffItem o4 = it("Stud", "12'", null, null, "", null); o4.material = "2X6"; o4.species = "DF.No2"; o4.group = g1;  // no QTY -> skipped
        TakeoffItem o5 = it("Note", "", null, null, "", 3.0);     o5.group = g1;                                               // empty ItemKey -> skipped
        MaterialDbEntry od = new MaterialDbEntry(); od.material = "2X4"; od.length = "12'"; od.species = "DF.No2"; od.unitPriceOutTax = 10.0; od.supply = "ACME";
        Supplier os = new Supplier(); os.name = "ACME"; os.tax = 8.25;
        Map<String, Map<String, CalcEngine.OrderedLine>> agg =
            CalcEngine.aggregateByGroup(Arrays.asList(o1, o2, o3, o4, o5), Arrays.asList(od), Arrays.asList(os));
        CalcEngine.OrderedLine l24 = agg.get(g1).get("2x4|12'|df.no2");
        check("ordered: same key in same group is summed (2+3)", l24.qty, 5);
        check("ordered: unit price with tax", Math.abs(l24.unit - 10.825) < 1e-9, true);
        check("ordered: line total = 5 * 10.825", Math.abs(l24.total() - 54.125) < 1e-9, true);
        check("ordered: supply from Materials DB", l24.supply, "ACME");
        check("ordered: blank GROUP becomes (sem grupo)", agg.containsKey(CalcEngine.NO_GROUP), true);
        check("ordered: key not in DB has no unit price", agg.get(CalcEngine.NO_GROUP).get("hanger|hangers_clips").unit, null);
        check("ordered: lines without QTY or ItemKey are skipped", agg.get(g1).size(), 1);
        check("ordered: group order = canonical first, then others",
            CalcEngine.groupDisplayOrder(new LinkedHashSet<>(Arrays.asList(CalcEngine.NO_GROUP, g1)), SeedData.GROUPS),
            Arrays.asList(g1, CalcEngine.NO_GROUP));
        check("ordered: CSV header + first row (as the web export)",
            com.nlc.materiallist.ui.OrderedPanel.buildCsv(agg).split("\n")[1],
            "1ST FLOOR - WALL,2X4,12',DF.No2,5,ACME,10.82,54.13");  // same as JS: (10.825).toFixed(2), (10.825*5).toFixed(2)
        check("fixed2 matches JS toFixed(2) (10.825 -> 10.82)", CalcEngine.fixed2(10.825), "10.82");
        check("money matches JS (1234.5 -> $1,234.50)", CalcEngine.money(1234.5), "$1,234.50");
        Path dbFile = Paths.get(System.getProperty("user.home"), "NextLevelConstruction", "material_list.db");
        check("db file created under user.home", Files.exists(dbFile), true);
        System.out.println("RESULT pass=" + pass + " fail=" + fail);
        System.exit(fail == 0 ? 0 : 1);
    }
}
