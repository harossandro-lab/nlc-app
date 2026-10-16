# Next Level Construction — Material List app (job: AVENEL)

Replaces Next Level Construction's Excel/VBA material-takeoff workbooks with an app the whole team can use.
The user (Sandro) is a construction professional and writes in Brazilian Portuguese.
Last verified 2026-10-16: Java build + `test/SmokeCheck.java` (33/33) on JDK 21 (Linux) and JDK 25 (Windows 11, PowerShell block below); web app exercised in headless Chromium.

## Working agreements
- Talk to the user in Brazilian Portuguese (pt-BR), in plain language. Code, identifiers, comments and commit messages stay in English.
- The Excel workbook is the source of truth. Fidelity is mandatory: never simplify a formula, list or label.
  If the app and the workbook disagree, the workbook wins — ask before deviating.
- Analyze first, then implement. For a bug: explain the root cause before patching, then re-test.
- Work in small, numbered, reversible steps. If this folder is not a git repo yet, run `git init` and commit the
  imported baseline before changing anything; commit after each verified step.
- Never edit anything in `reference/` (read-only spec).

## Layout
- `reference/AVENEL_Material_List_05-07-2026.xlsm` — authoritative workbook (user's file "Material List - (05.07.2026).xlsm").
- `reference/ME-Wood_Russo_Material_List.xlsm` — earlier workbook (user's file "Material List - ME Wood - Russo.xlsm").
- `web/index.html` — single-file HTML/JS app, build "app8" (vanilla JS, no build step; Google Fonts Oswald/Inter/IBM Plex Mono).
- `NextLevelConstruction/` — Java 17+ / Swing / SQLite desktop base, an Eclipse project (`.project`, `.classpath`; its README.md is in pt-BR).
  The user edits/runs it in Eclipse: after you change files, tell them to press F5 on the project in Eclipse.

## What the user asked for
- One app that replaces the whole spreadsheet, usable on Windows, macOS, iPhone and iPad; the team uses it at the same time (sync between people/devices).
- Home screen = one circle per job (2–5 letter abbreviation, e.g. AVN = AVENEL) plus "New Job". Jobs are fully independent.
- Inside a job, a second circle screen in spreadsheet order: Dashboard, Sub-Floor, 1st–6th Floor Walls, Roof, Flush Beam, Shaft Wall,
  Stair Tower, Balcony, Windows & Doors, then Ordered (auto), Received, Audit Log, Materials DB, Suppliers & Tax.
- TAKEOFF / Ordered must be automatic (in Excel it is consolidated by hand).
- Fixed GROUP list exactly as in the workbook. Audit log of quantity changes. Received tracking with ticket / invoice / date.
- Dependent dropdowns: pick SPECIES first, then MATERIAL is limited to that species (DATE-BASE).
- Look: dark navy #10233B, orange #E2600C accent, ruler strip. Labels follow the workbook (English); a few helper texts are pt-BR.

## Business logic (authoritative: the workbook's LET() formula and VBA)
Code: `NextLevelConstruction/src/com/nlc/materiallist/calc/CalcEngine.java` and, in `web/index.html`, `computeQty`, `buildItemKey`,
`itemKeyOf`, `unitPriceOf`, `aggregateByGroup`. Both implementations must stay identical.
QTY of a take-off line — first matching rule wins, then waste and rounding:
1. PURPOSE contains "end stud" → `LF*2/12`
2. spacing present and LF>0 → `LF*12/spacing_in` (× EA when EA>0)
3. SP has "N Ply" → `N*LF/length` (needs LF and length), else `N*EA`
4. otherwise `LF/length`, else `SF/length`, else `EA`
5. ×1.05 when PURPOSE contains both "sheathing" and "roof"; round UP to a whole piece; not enough data → blank.
- LENGTH parsing: strip `'`, `"`, `SF`; mixed fractions work (`104 5/8"` = 104.625); blank or `N/A` = no length.
- SP parsing: plain number = inches; `16"` = 16; `4'` = 48; `2 Ply` = ply count (spacing and ply never both).
- ItemKey = `MATERIAL|LENGTH|SPECIES`; empty parts and an `N/A` length are omitted (no empty segments); compared case-insensitively.
- Price: `unit = unitPriceOutTax × (1 + supplierTax%/100)`; line total = QTY × unit; supplier matched by name, ignoring case.
- Ordered (auto) = sum of QTY by GROUP → ItemKey across all sections (replaces the manual TAKEOFF sheet + `Update_ORDERED_All`).
- Audit log = diff of ItemKey totals before/after an edit → ADDED / CHANGED / REMOVED (web: snapshot 1.4 s after a change, last 400 entries).
- Received (web tab RCV) row = group, location, supply, date, material, length, species, qty, ticket, invoice, payment.

## Workbook map (AVENEL, 24 sheets) — read with openpyxl
- HOME, DASHBOARD — navigation and KPIs.
- 13 take-off tabs: `SUB-FLOOR ` (**the sheet name has a trailing space**), 1ST-WALLS … 6TH-WALLS, ROOF, FLUSH-BEAM, SHAFT WALL,
  STAIR-TOWER, BALCONY, WINDOWS. Columns: PURPOSE, PAGE/DETAIL, MATERIAL, LENGTH, SPECIES, LF, SF, SP, EA, LOCATION, QTY (LET formula).
- SETTINGS — Excel tables `LENGTH` (F8), `SPACIENG` [sic] (G8), `LOCATION` (K8), `tblGroup` (L8); each has spare blank rows.
- DATE-BASE — row 7 (A7:Y7) holds the 25 species; each column below is that species' MATERIAL list.
  Take-off dropdowns: SPECIES = named range `CATEGORIA2.0`; MATERIAL = `INDIRECT(<SPECIES cell of the row>)`.
- TAKEOFF — manual consolidation by GROUP (automatic in the app). ORDERED and RECEIVED (+ `_DV_RECEIVED`: helper lists for the
  dependent GROUP→LOCATION→SUPPLY dropdowns).
- PRICE (`tblSupplyTax` = supplier + tax %, `tblPriceManual`, …); DATABASE (veryHidden, Power Query `Q_DATABASE`) = master price table
  keyed by Material|Length|Species; PRICE_AUDIT (veryHidden). Many more tables: `tblOrderedAll`, `tblDelivered*`, `tblDash*`.
- VBA: `RefreshAll_Safe` (Module1), `Update_ORDERED_All` + `BuildItemKey` (Module2), `Refresh_RECEIVED` / `Setup_RECEIVED` (Module3),
  `modReceivedDV`, `modTicketLinks`, `modSheetProtection`, `modTable*`.

## Seed lists (web `SEED` and Java `SeedData` come from the same data — keep them in sync)
- GROUP: 43 values, identical to SETTINGS `tblGroup` (verified), including the original typo `SUB-LOOR` and the double space in
  `BALCONY - FRONT  ELEVATION`. Never "fix" them. (Early in the chat the list was called "42"; the real count is 43.)
- Default GROUP per section: sub-floor→`SUB-LOOR - WALL`; 1st…6th-walls→`1ST FLOOR - WALL`…`6TH FLOOR - WALL`; roof→`ROOF`;
  flush-beam→(none); shaft-wall→`SHAFT WALL - 1`; stair-tower→`STAIR TOWER - 1`; balcony→`BALCONY - FRONT  ELEVATION`; windows→`WINDOWS`.
- LOCATION: FACTORY, FIELD (identical). LENGTH: the 22 workbook values plus `116 5/8"` (it comes from the ME Wood workbook, SETTINGS!F31).
- SPACING: 9 values in the workbook's SETTINGS order (`10'`, `12"`, `16"`, `24"`, `32"`, `4'`, `6'`, `8'`, `8"`); fixed in both tracks and covered by SmokeCheck.
- 13 sections (each with its real PURPOSE list): sub-floor, 1st…6th-walls, roof, flush-beam, shaft-wall, stair-tower, balcony, windows.
  25 species with about 500 species→material options.

## Web app (`web/index.html`)
- Vanilla JS in one file; `SEED` (~line 205) holds the seed data. Navigation: `bottomView` (home|list|config|more),
  `homeLevel` (home|project-menu|shell), `backOneLevel()`. The 19 job circles are `TAB_CIRCLES`.
- Persistence is `window.storage.get(key, true)` / `.set(key, value, true)` (shared mode) — **this API exists only inside Claude artifacts.**
  Keys: `projects-list`, and per job `proj:<id>:` + `project-info | database | suppliers | received-log | audit-log | audit-snapshot | items-all`
  (`items-all` holds all 13 sections in ONE key).
- Sync layer: `markDirty` → `flushDirty` (500 ms debounce, 8 s background retry, flush on `visibilitychange`); indicator
  synced / syncing… / "not synced yet — retry". No `console.error/warn` by design.
- Outside Claude (verified in headless Chromium): without `window.storage` the page stays on "Loading…" (the indicator still says
  "synced") and nothing is saved. With a ~8-line localStorage shim that implements only `get` and `set` (both return Promises; `get`
  resolves `{value}` or `null`) the whole app works: Home → AVN → 19 circles, and data survives a reload.

## Java app (`NextLevelConstruction/`)
- Package `com.nlc.materiallist`: `calc/CalcEngine` (ALL business logic), `data/SeedData` (generated from the web seed), `db/Database`,
  `dao/*`, `model/*`, `ui/*`.
- Data: one SQLite file for all jobs at `~/NextLevelConstruction/material_list.db`; tables `projects`, `project_info`, `suppliers`,
  `materials_db`, `takeoff_items`, all keyed by `project_id` (ON DELETE CASCADE); schema in `resources/schema.sql`, read from the classpath.
- UI: `MainFrame` (CardLayout) → `HomePanel` → `ProjectMenuPanel` (circles) → `DashboardPanel` / generic `SectionPanel`
  (JTable + `TakeoffTableModel`) / `MaterialsDbPanel` / `SuppliersPanel`. `MaterialCellEditor` rebuilds the MATERIAL combo from the
  row's SPECIES every time the cell is edited. Every edit is written to SQLite immediately (no save button).
- Local only — no sync between people. Pin `lib/sqlite-jdbc-3.36.0.3.jar` (3.46.x needs slf4j and fails with NoClassDefFoundError).

## Build, run, check (from `NextLevelConstruction/`; verified with JDK 21 and `--release 17`)
```bash
mkdir -p bin
javac --release 17 -encoding UTF-8 -cp lib/sqlite-jdbc-3.36.0.3.jar -d bin $(find src -name "*.java")
java -cp "bin:resources:lib/sqlite-jdbc-3.36.0.3.jar" com.nlc.materiallist.Main     # GUI, needs a display
# logic check without GUI; a throwaway user.home keeps the real database untouched. Expect: RESULT pass=33 fail=0
javac --release 17 -cp "bin:lib/sqlite-jdbc-3.36.0.3.jar" -d /tmp/nlc-smoke test/SmokeCheck.java
java -Duser.home=/tmp/nlc-home -cp "/tmp/nlc-smoke:bin:resources:lib/sqlite-jdbc-3.36.0.3.jar" SmokeCheck
```
Windows PowerShell (tested on Windows 11 with JDK 25, `--release 17`: compiles and SmokeCheck passes; the JDK 25 "restricted method" warning from sqlite-jdbc is harmless):
```powershell
New-Item -ItemType Directory -Force bin | Out-Null
$src = Get-ChildItem -Recurse src -Filter *.java | ForEach-Object FullName
javac --release 17 -encoding UTF-8 -cp lib\sqlite-jdbc-3.36.0.3.jar -d bin $src
java -cp "bin;resources;lib\sqlite-jdbc-3.36.0.3.jar" com.nlc.materiallist.Main
javac --release 17 -cp "bin;lib\sqlite-jdbc-3.36.0.3.jar" -d "$env:TEMP\nlc-smoke" test\SmokeCheck.java
java "-Duser.home=$env:TEMP\nlc-home" -cp "$env:TEMP\nlc-smoke;bin;resources;lib\sqlite-jdbc-3.36.0.3.jar" SmokeCheck
```
- Classpath separator: `:` on Linux/macOS, `;` on Windows (also in Git Bash). `resources` must be on the runtime classpath, otherwise startup
  fails with "schema.sql not found on classpath" (Eclipse handles it through `.classpath`).
- The GUI cannot run headless. Swing components can still be built and driven without a display for UI-flow tests. The real look was never
  confirmed on a display — ask the user for a screenshot after the first run.

## Pitfalls already hit (don't repeat)
- `<datalist>` inside `<tr>`/`<table>` is invalid HTML: browsers move it and `row.querySelector` returns null. Render datalists after the
  table and find them with `getElementById` (ids like `dl-mat-<section>-<row>`).
- Never fire many storage writes at once (opening a job once wrote ~16 keys → "Internal server error"). Keep one `items-all` key,
  batch through the dirty map, retry silently.
- Swing table models need explicit `projectId` and `sectionId`; inferring them from existing rows broke empty sections.

## Known gaps / backlog (propose this order to the user and confirm)
1. **Team sync** is the main unmet requirement: the web app only syncs inside Claude artifacts; the Java app is local SQLite only. Needs a
   decision with the user (e.g. a hosted database such as Supabase/Firebase, or a small server). Then put the choice behind a
   `get(key)` / `set(key, value)` adapter that replaces `window.storage`, so the rest of the app stays unchanged.
2. Make the web app usable outside Claude: the localStorage adapter (single user, offline) is the first step toward #1.
3. ~~Fix the SPACING seed (`8'` missing)~~ — DONE (web `SEED` and `SeedData.SPACINGS`, workbook order, SmokeCheck covers it).
4. Java: add the 12 missing section tiles in `ProjectMenuPanel.TILES` (ids match `SeedData.SECTIONS`: `1st-walls`, `2nd-walls`, …); port
   Ordered (auto), Received and Audit Log from the web app; add a Config screen and a real "Lista" (the bottom nav reuses Home).
5. Data: neither app has the real price list or suppliers yet (web seed: one example material `2X4|12'|DF.No2`, suppliers FACTORY/FIELD
   at 0% tax). Import them from the workbook (DATABASE / PRICE) and, if the user wants, the existing AVENEL take-off lines.
6. Cleanup: dead `SectionPanel.refresh()`; duplicated FEET matcher lines in `CalcEngine.parseSpacingAndPly`; unchecked warning in
   `MaterialCellEditor`; `MainFrame` re-adds panels under the same CardLayout name without removing the old ones.
7. Tests: grow `test/SmokeCheck.java` into one case per QTY rule, using values computed by the workbook itself.
