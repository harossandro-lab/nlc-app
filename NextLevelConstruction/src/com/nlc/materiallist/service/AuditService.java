package com.nlc.materiallist.service;

import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.swing.SwingUtilities;
import javax.swing.Timer;

import com.nlc.materiallist.calc.CalcEngine;
import com.nlc.materiallist.calc.CalcEngine.AuditChange;
import com.nlc.materiallist.calc.SectionOrder;
import com.nlc.materiallist.dao.AuditDao;
import com.nlc.materiallist.dao.TakeoffItemDao;

/**
 * Keeps the audit log: after an edit it compares the ItemKey totals with the last snapshot and records
 * ADDED / CHANGED / REMOVED, like the web app's runAuditDiff (1.4 s after the last change, last 400 entries).
 */
public final class AuditService {

    /** Debounce between the last edit and the comparison (same as the web app). */
    public static final int DELAY_MS = 1400;

    private static final AuditDao dao = new AuditDao();
    private static final TakeoffItemDao itemDao = new TakeoffItemDao();
    private static final Map<String, Timer> timers = new HashMap<>();

    private AuditService() {}

    /** Current totals per ItemKey, sections in workbook order. */
    private static Map<String, Integer> currentTotals(String projectId) {
        return CalcEngine.totalsByItemKey(SectionOrder.sort(itemDao.findByProject(projectId)));
    }

    /**
     * First time a job is opened (no snapshot and no log yet) the current state becomes the baseline, without
     * creating entries — the same rule as the web app's openProject.
     */
    public static synchronized void ensureBaseline(String projectId) {
        if (dao.getSnapshot(projectId).isEmpty() && dao.countLog(projectId) == 0) {
            dao.saveRun(projectId, Instant.now().toString(), List.of(), currentTotals(projectId));
        }
    }

    /** Compares now with the snapshot and records the differences. Returns how many entries were added. */
    public static synchronized int runDiff(String projectId) {
        Map<String, Integer> current = currentTotals(projectId);
        List<AuditChange> diffs = CalcEngine.auditDiff(dao.getSnapshot(projectId), current);
        if (diffs.isEmpty()) return 0;
        dao.saveRun(projectId, Instant.now().toString(), diffs, current);
        return diffs.size();
    }

    /** Called after every take-off edit: runs the comparison once the edits stop for DELAY_MS. */
    public static void schedule(String projectId) {
        SwingUtilities.invokeLater(() -> {
            Timer t = timers.get(projectId);
            if (t != null) t.stop();
            t = new Timer(DELAY_MS, e -> runDiff(projectId));
            t.setRepeats(false);
            timers.put(projectId, t);
            t.start();
        });
    }
}
