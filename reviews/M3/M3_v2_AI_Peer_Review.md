# AI Peer Review — M3 Domain Model, re-review (v2)

## 1. Executive Summary

Stort, verkligt framsteg — men fortfarande **RE_REVIEW_REQUIRED**. Jag körde hela testsviten igen. Godkända tester gick från 10/39 (26%) till **23/40 (57,5%)**. Produktionskoden är nu genuint korrekt fixad på alla punkter jag flaggade förra rundan: `StatusSample` har rätt fältnamn, alla sju valideringsregler, kompletta enums; `interval_summary.py`s egen källkod importerar korrekt `QualityLevel` i stället för den fantom-`MeasurementQuality` som aldrig existerade; kontraktet har fått en explicit evalueringsordning (`DM-INTERVAL-SUMMARY-013`); enum-casing är nu konsekvent (allt gemener).

**Men testfilerna följde inte med.** Två testfiler konstruerar fortfarande objekt enligt den gamla, redan övergivna kontraktsformen:

- `test_measurement_window.py`s egen lokala `sample()`-hjälpfunktion (rad 14) använder fortfarande `pll_lock=` — fältet heter `pll_locked` i den redan fixade `StatusSample`. 7 av 10 tester i den filen misslyckas av just den anledningen.
- `test_interval_summary.py` importerar fortfarande den numera bekräftat obefintliga `MeasurementQuality` — och när jag (rent diagnostiskt, i en lokal kopia, inte i era filer) patchade om det namnet upptäckte jag att testets `observation()`-hjälpfunktion (rad 19) dessutom konstruerar `Observation` med fält som inte finns (`classification_snr_db` — det är en beräknad `@property`, inte ett konstruktorargument; `classification_reason` — det korrekta fältet heter `reason_code`) och saknar flera obligatoriska fält helt (`verification_snr_db`, `ka9q_reported_snr_db`, `verification_quality`, `identification_quality`, `verification_accepted`). Den här testfilen har alltså aldrig kunnat köras mot den `Observation`-form som faktiskt existerar, i någon version av paketet jag sett.

`DM3-F-006` (ingen `test_observation.py`) är inte adresserad alls den här rundan.

## 2. Review Decision

**RE_REVIEW_REQUIRED** (1 CRITICAL, 2 HIGH kvarstår — men noll av mina tidigare produktionskodsfynd)

## 3. Status på förra rundans fynd

| Fynd | Status |
|---|---|
| DM3-F-001 (`__init__.py` exporterade bara 2/12 symboler) | **Stängt.** Alla 12 publika symboler exporteras nu korrekt. |
| DM3-F-002 (`interval_summary.py` importerade obefintlig `MeasurementQuality`) | **Källkoden stängd, testfilen inte.** `interval_summary.py` importerar nu korrekt `QualityLevel` och `_classify_quality` returnerar riktiga `QualityLevel`-medlemmar. Se nytt fynd DM3.1-F-001. |
| DM3-F-003 (`pll_lock`/`pll_locked`, saknat `sequence_number`) | **Källkoden stängd.** Se nytt fynd DM3.1-F-002 för testfilsavvikelsen. |
| DM3-F-004 (ofullständiga enums) | **Stängt.** `DemodMode` har alla 5 värden, `SampleQuality` har `PARTIAL`. |
| DM3-F-005 (saknad validering) | **Stängt.** Samtliga 7 regler implementerade och verifierat körda gröna i `test_status_sample.py` (9/9). |
| DM3-F-006 (ingen `test_observation.py`) | **Ej adresserat.** |
| DM3-F-007 (odokumenterad evalueringsordning) | **Stängt.** Ny `DM-INTERVAL-SUMMARY-013`. |
| DM3-F-008 (inkonsekvent enum-casing) | **Stängt.** Allt gemener nu, konsekvent mellan `DetectionState` och `SummaryState`. |

## 4. Nya fynd

### DM3.1-F-001 — CRITICAL — Test/code lag
**AKB section:** `DM-INTERVAL-SUMMARY.md` · **Python:** `src/ka9q_beacon_monitor/model/interval_summary.py` (redan korrekt) · **Test:** `tests/model/test_interval_summary.py:5-11, 19`

**Finding:** Källkoden fixades korrekt att använda `QualityLevel`, men `test_interval_summary.py` uppdaterades aldrig — den importerar fortfarande `MeasurementQuality` och skulle, även efter en namnbytesfix, fortfarande misslyckas eftersom dess `observation()`-hjälpfunktion konstruerar `Observation` med obefintliga fält (`classification_snr_db`, `classification_reason`) och saknar flera obligatoriska fält (`verification_snr_db`, `ka9q_reported_snr_db`, `verification_quality`, `identification_quality`, `verification_accepted`).

**Evidence (körd):**
```
$ python3 -m pytest -q
ImportError: cannot import name 'MeasurementQuality' from 'ka9q_beacon_monitor.model'
```
Diagnostisk lokal patchning (namnbyte enbart) gav sedan:
```
TypeError: Observation.__init__() got an unexpected keyword argument 'classification_snr_db'
7 failed, 3 passed
```

**Impact:** Samtliga 10 tester i filen är overifierade. `IntervalSummary`s aggregeringslogik (`DM-INTERVAL-SUMMARY-001` till `-013`) har fortfarande aldrig körts en enda gång i det här paketet, trots att den underliggande produktionskoden nu ser korrekt ut vid manuell läsning.

**Recommendation:** Skriv om `test_interval_summary.py`s `observation()`-hjälpfunktion mot den faktiska `Observation`-signaturen (inklusive alla obligatoriska fält), och byt `MeasurementQuality` → `QualityLevel` (med rätt medlemsnamn — `VALID` finns inte, troligen menat `NOMINAL`).

**Verification test:** `pytest tests/model/test_interval_summary.py` ska samlas in och köras utan fel.

**Confidence:** 1.0

---

### DM3.1-F-002 — HIGH — Test/code lag
**AKB section:** `DM-STATUS-SAMPLE.md` · **Python:** `src/ka9q_beacon_monitor/model/status_sample.py` (redan korrekt) · **Test:** `tests/model/test_measurement_window.py:14-25`

**Finding:** `test_status_sample.py` uppdaterades korrekt till `pll_locked` (och passerar 9/9), men `test_measurement_window.py`s egen, separata `sample()`-hjälpfunktion missades och använder fortfarande `pll_lock=None`.

**Evidence (körd):**
```
$ python3 -m pytest tests/model/test_measurement_window.py -q
TypeError: StatusSample.__init__() got an unexpected keyword argument 'pll_lock'
7 failed, 3 passed in 0.03s
```

**Impact:** 7 av 10 tester i filen misslyckas trots att både `MeasurementWindow` och `StatusSample` (baserat på min läsning och på `test_status_sample.py`s gröna resultat) är korrekt implementerade.

**Recommendation:** Byt `pll_lock=` → `pll_locked=` på rad 24 i `test_measurement_window.py`. Överväg att låta båda testfilerna dela en gemensam `make_status_sample()`-hjälpfunktion för att undvika att den här typen av dubblettdrift händer igen.

**Verification test:** `pytest tests/model/test_measurement_window.py` ska visa 10/10 gröna.

**Confidence:** 1.0

---

### DM3.1-F-003 — HIGH — Oförändrat sedan förra rundan
**Finding:** `tests/model/test_observation.py` saknas fortfarande (se DM3-F-006). `Observation` har alltjämt noll körda tester i paketet.

**Confidence:** 0.95

## 5. Contract/Code Coverage Matrix

| DM Contract | Källkod matchar kontrakt | Tester körbara | Tester gröna |
|---|---|---|---|
| DM-STATUS-SAMPLE | **Ja, verifierat** | Ja | **9/9** |
| DM-MEASUREMENT-WINDOW | Ja (manuell läsning; koden själv ändrades inte denna runda) | Ja | 3/10 (testfilsbugg, ej kodbugg) |
| DM-OBSERVATION | Ja (manuell läsning) | N/A — ingen testfil | 0/0 |
| DM-INTERVAL-SUMMARY | **Ja, källkoden korrigerad** | **Nej** (testfilen fortfarande trasig, dessutom djupare avvikelser) | 0/10 |
| DM-DATABASE | Ja | Ja | 6/6 |

## 6. Requirements Traceability Gaps

- `DM-OBSERVATION` → `TEST-DM-OBSERVATION`: fortfarande ingen testfil (oförändrat).
- Testfilerna för `MeasurementWindow` och `IntervalSummary` är nu det enda som separerar paketet från en grön build — inte produktionskoden.

## 7. Unverified Assumptions

- Jag har inte kunnat exekvera `IntervalSummary`s faktiska aggregeringslogik (trösklar, `_classify_summary`) mot verkliga `Observation`-objekt, eftersom testfilen inte går att reparera med en enkel namnbytespatch. Min bedömning av att produktionskoden är korrekt bygger fortsatt på manuell läsning för den delen, inte körning.

## 8. Recommended Edits

1. Skriv om `test_interval_summary.py`s `observation()`-hjälpfunktion helt mot den faktiska `Observation`-signaturen (DM3.1-F-001).
2. Byt `pll_lock` → `pll_locked` i `test_measurement_window.py` rad 24 (DM3.1-F-002).
3. Lägg till `tests/model/test_observation.py` (DM3.1-F-003 / gamla DM3-F-006).
4. När ovanstående är löst, kör om hela sviten och bekräfta 40/40 gröna.

## JSON

```json
{
  "review_summary": {
    "decision": "RE_REVIEW_REQUIRED",
    "confidence": 0.95,
    "executed_test_results": {"declared": 40, "passed": 23, "failed": 7, "not_collected": 10},
    "previous_run": {"declared": 39, "passed": 10, "failed": 9, "not_collected": 20},
    "top_risks": [
      "test_interval_summary.py still cannot be collected and, once patched for the rename, reveals its Observation-construction helper is fundamentally out of sync with the real dataclass (DM3.1-F-001)",
      "test_measurement_window.py's own sample() helper was not updated for the pll_lock -> pll_locked rename (DM3.1-F-002)"
    ]
  },
  "findings": [
    {"id": "DM3.1-F-001", "severity": "CRITICAL", "category": "Test/code lag", "akb_section": "DM-INTERVAL-SUMMARY.md", "python_location": "src/ka9q_beacon_monitor/model/interval_summary.py (already correct)", "test_location": "tests/model/test_interval_summary.py:5-11,19", "finding": "Production code correctly fixed to use QualityLevel, but the test file still imports the nonexistent MeasurementQuality, and its observation() helper constructs Observation with nonexistent fields and missing required fields.", "evidence": "ImportError on collection; diagnostic local patch then shows TypeError for classification_snr_db and missing required args, 7 of 10 tests still fail.", "impact": "All 10 tests in the file remain unverified; IntervalSummary aggregation logic has still never been executed in this package.", "recommendation": "Rewrite the observation() helper against the real Observation signature and fix the MeasurementQuality reference.", "verification_test": "pytest tests/model/test_interval_summary.py collects and runs cleanly.", "confidence": 1.0},
    {"id": "DM3.1-F-002", "severity": "HIGH", "category": "Test/code lag", "akb_section": "DM-STATUS-SAMPLE.md", "python_location": "src/ka9q_beacon_monitor/model/status_sample.py (already correct)", "test_location": "tests/model/test_measurement_window.py:14-25", "finding": "test_status_sample.py was correctly updated for the pll_lock->pll_locked rename, but test_measurement_window.py's separate local sample() helper was missed.", "evidence": "TypeError: StatusSample.__init__() got an unexpected keyword argument 'pll_lock'; 7 of 10 tests fail.", "impact": "7 of 10 tests fail despite MeasurementWindow and StatusSample both being correctly implemented.", "recommendation": "Fix pll_lock to pll_locked on line 24; consider sharing one status-sample test helper across files.", "verification_test": "pytest tests/model/test_measurement_window.py shows 10/10 passing.", "confidence": 1.0},
    {"id": "DM3.1-F-003", "severity": "HIGH", "category": "Test coverage", "akb_section": "DM-OBSERVATION.md", "python_location": "src/ka9q_beacon_monitor/model/observation.py", "test_location": "(still missing) tests/model/test_observation.py", "finding": "No dedicated Observation test file exists yet; unchanged from the prior review.", "evidence": "find tests -iname '*observation*' returns nothing.", "impact": "Observation still has zero executed test coverage.", "recommendation": "Add tests/model/test_observation.py.", "verification_test": "New file exists and passes.", "confidence": 0.95}
  ],
  "resolved_since_previous_review": ["DM3-F-001", "DM3-F-002 (production code)", "DM3-F-003", "DM3-F-004", "DM3-F-005", "DM3-F-007", "DM3-F-008"],
  "requirements_traceability_gaps": [
    "DM-OBSERVATION's declared TEST-DM-OBSERVATION still does not exist as a file."
  ],
  "unverified_assumptions": [
    "IntervalSummary's actual aggregation/threshold logic still could not be executed against real Observation objects; correctness assessment remains based on manual reading."
  ],
  "recommended_edits": [
    "Rewrite test_interval_summary.py's observation() helper against the real Observation signature (DM3.1-F-001).",
    "Fix pll_lock to pll_locked in test_measurement_window.py (DM3.1-F-002).",
    "Add tests/model/test_observation.py (DM3.1-F-003).",
    "Re-run the full suite and confirm 40/40 green."
  ]
}
```
