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
        wantTiles.add("database"); wantTiles.add("suppliers");
        check("menu tiles = dashboard + 13 sections + db + suppliers", tileIds, wantTiles);
        check("menu tile count", tileIds.size(), 16);
        System.setProperty("java.awt.headless", "true");
        com.nlc.materiallist.model.Project proj = new com.nlc.materiallist.dao.ProjectDao().create("TST", "Smoke");
        new com.nlc.materiallist.ui.ProjectMenuPanel(proj, id -> {});
        int built = 0;
        for (SeedData.Section sec : SeedData.SECTIONS) {
            new com.nlc.materiallist.ui.SectionPanel(proj, sec.id);
            built++;
        }
        check("SectionPanel builds for every section", built, 13);
        Path dbFile = Paths.get(System.getProperty("user.home"), "NextLevelConstruction", "material_list.db");
        check("db file created under user.home", Files.exists(dbFile), true);
        System.out.println("RESULT pass=" + pass + " fail=" + fail);
        System.exit(fail == 0 ? 0 : 1);
    }
}
