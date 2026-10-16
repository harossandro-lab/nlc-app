package com.nlc.materiallist.model;

/**
 * One delivery in the Received log: group, location, supply, date, material, length, species,
 * qty, ticket, invoice and payment (same fields as the web app's received-log).
 */
public class ReceivedEntry {
    public Long id;
    public String projectId;
    public String group = "";
    public String location = "FACTORY";
    public String supply = "";
    public String date = "";     // yyyy-MM-dd, as the web date input stores it
    public String material = "";
    public String length = "";
    public String species = "";
    public Double qty;           // null = not filled in yet
    public String ticket = "";
    public String invoice = "";
    public String payment = "";
}
