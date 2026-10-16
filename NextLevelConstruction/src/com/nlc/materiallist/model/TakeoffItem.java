package com.nlc.materiallist.model;

/**
 * One line item in a takeoff section (Sub-Floor, 1st-Walls, etc.)
 * Field names and meaning mirror the original spreadsheet columns exactly:
 * PURPOSE, PAGE/DETAIL, MATERIAL, LENGTH, SPECIES, LF, SF, SP, EA, LOCATION,
 * plus GROUP (added so "Ordered" can auto-aggregate) and STATUS (Pending/Ordered/Received).
 */
public class TakeoffItem {
    public Long id;              // DB row id (null = not yet saved)
    public String projectId;
    public String sectionId;     // e.g. "sub-floor"
    public String group = "";    // one of the 43 canonical GROUP values
    public String purpose = "";
    public String pageDetail = "";
    public String material = "";
    public String length = "";
    public String species = "";
    public Double lf;
    public Double sf;
    public String sp = "";       // spacing text: "16", "24", "2 Ply", "2' O.C." ...
    public Double ea;
    public String location = "FACTORY";
    public String status = "pending"; // pending | ordered | received

    public TakeoffItem() {}

    public TakeoffItem copy() {
        TakeoffItem t = new TakeoffItem();
        t.id = id; t.projectId = projectId; t.sectionId = sectionId; t.group = group;
        t.purpose = purpose; t.pageDetail = pageDetail; t.material = material;
        t.length = length; t.species = species; t.lf = lf; t.sf = sf; t.sp = sp; t.ea = ea;
        t.location = location; t.status = status;
        return t;
    }
}
