package com.nlc.materiallist.calc;

import java.util.ArrayList;
import java.util.List;

import com.nlc.materiallist.data.SeedData;
import com.nlc.materiallist.model.TakeoffItem;

/** Workbook section order for take-off lines (the web app walks the sections in this order). */
public final class SectionOrder {

    private SectionOrder() {}

    /** Items sorted by section in workbook order, then by row id. */
    public static List<TakeoffItem> sort(List<TakeoffItem> items) {
        List<String> order = new ArrayList<>();
        for (SeedData.Section s : SeedData.SECTIONS) order.add(s.id);
        List<TakeoffItem> out = new ArrayList<>(items);
        out.sort((a, b) -> {
            int c = Integer.compare(order.indexOf(a.sectionId), order.indexOf(b.sectionId));
            if (c != 0) return c;
            return Long.compare(a.id == null ? 0 : a.id, b.id == null ? 0 : b.id);
        });
        return out;
    }
}
