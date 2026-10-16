package com.nlc.materiallist.model;

/** A supplier with its tax rate — mirrors the tblSupplyTax table on the original PRICE sheet. */
public class Supplier {
    public Long id;
    public String projectId;
    public String name = "";
    public double tax = 0.0;   // percent
    public int delay = 0;      // days
}
