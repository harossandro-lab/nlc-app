package com.nlc.materiallist.model;

/** A job/project — mirrors one "circle" on the Home screen. */
public class Project {
    public String id;
    public String abbr;
    public String name;
    public String createdAt;

    public Project() {}

    public Project(String id, String abbr, String name, String createdAt) {
        this.id = id;
        this.abbr = abbr;
        this.name = name;
        this.createdAt = createdAt;
    }
}
