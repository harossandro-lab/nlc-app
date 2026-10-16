package com.nlc.materiallist.model;

/** One row of the Materials Database (pricing catalog), keyed by Material|Length|Species. */
public class MaterialDbEntry {
    public Long id;
    public String projectId;
    public String material = "";
    public String length = "";
    public String species = "";
    public String supply = "FACTORY";
    public double unitPriceOutTax = 0.0;
}
