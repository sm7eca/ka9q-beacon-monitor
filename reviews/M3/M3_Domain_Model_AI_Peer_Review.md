# AI Peer Review — M3 Domain Model (REVIEW-M3-DOMAIN-MODEL)

## 1. Executive Summary

Jag verifierade paketets SHA-256-manifest (alla 19 filer stämmer), installerade paketet och **körde testsviten själv** i stället för att bara läsa koden. Resultatet: av 39 deklarerade tester i `tests/` **kör bara 10 (26%) grönt**. Nio tester i `test_status_sample.py` misslyckas (100% av den filen), och tjugo tester fördelade över `test_interval_summary.py` och `test_measurement_window.py` **kan inte ens samlas in** — `pytest` kraschar vid import.

Grundorsaken är strukturell, inte kosmetisk: `model/__init__.py` exporterar bara två av tolv publika symboler, och `interval_summary.py` importerar en klass (`MeasurementQuality`) som inte existerar någonstans i kodbasen — trots att `DM-INTERVAL-SUMMARY.md` uttryckligen kräver den som typ för `quality`-fältet. Utöver det har `StatusSample` ett omdöpt fält, ett helt saknat fält, två ofullständiga enums, och fem av sju dokumenterade valideringsregler helt oimplementerade.

`Observation` och `MeasurementWindow` är däremot — baserat på min manuella kontrakt-mot-kod-läsning — genuint välskrivna och kontraktstrogna. Problemet är koncentrerat till `StatusSample` och `IntervalSummary`, plus paketets exportstruktur.

## 2. Review Decision

**RE_REVIEW_REQUIRED** (flera CRITICAL-fynd)

## 3. Findings

### DM3-F-001 — CRITICAL — Package structure
**AKB section:** N/A (paketinfrastruktur) · **Python:** `src/ka9q_beacon_monitor/model/__init__.py` · **Test:** `tests/model/test_interval_summary.py`, `tests/model/test_measurement_window.py`

**Finding:** `__init__.py` exporterar bara `DatabaseConfig` och `RetentionPolicy`. Alla övriga publika modellklasser (`StatusSample`, `DemodMode`, `SampleQuality`, `MeasurementWindow`, `Observation`, `DetectionState`, `MeasurementSource`, `QualityLevel`, `IntervalSummary`, `SummaryState`) saknas i `__all__`.

**Evidence (körd, inte bara läst):**
```
$ python3 -m pytest -q
ERROR tests/model/test_interval_summary.py - ImportError: cannot import name 'DetectionState' from 'ka9q_beacon_monitor.model'
ERROR tests/model/test_measurement_window.py - ImportError: cannot import name 'DemodMode' from 'ka9q_beacon_monitor.model'
!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!!
```

**Impact:** Två av fem testfiler (20 av 39 tester) kan inte ens samlas in av pytest — de exekveras aldrig, oavsett om den underliggande logiken är korrekt.

**Recommendation:** Uppdatera `__init__.py` att re-exportera hela den publika modellytan.

**Verification test:** `python3 -m pytest -q` ska visa 0 collection errors.

**Confidence:** 1.0 (körd, inte antagen)

---

### DM3-F-002 — CRITICAL — IntervalSummary / Observation
**AKB section:** `DM-INTERVAL-SUMMARY.md` (Interfaces: `quality: MeasurementQuality`) · **Python:** `src/ka9q_beacon_monitor/model/interval_summary.py:10`, `_classify_quality` · **Test:** `tests/model/test_interval_summary.py`

**Finding:** `interval_summary.py` importerar `MeasurementQuality` från `observation.py` — en klass som inte existerar där (eller någon annanstans i kodbasen). `observation.py` definierar `QualityLevel` (`INVALID, DEGRADED, NOMINAL, HIGH`), inte `MeasurementQuality`. Även om importnamnet fixades matchar inte `_classify_quality`s faktiska returvärden (`MeasurementQuality.VERIFIED`, `.VALID`, `.DEGRADED`, `.INVALID`) `QualityLevel`s medlemmar över huvud taget — det är två konceptuellt olika enum-uppsättningar.

**Evidence (körd):**
```
$ python3 -c "import ka9q_beacon_monitor.model.interval_summary"
ImportError: cannot import name 'MeasurementQuality' from 'ka9q_beacon_monitor.model.observation'
```
Detta är oberoende av DM3-F-001 — modulen går inte att importera ens direkt.

**Impact:** Hela `IntervalSummary`-modulen — aggregeringslogiken, trösklarna, `from_observations`, `_classify_summary`, `_classify_quality` — är körd noll gånger. `DM-INTERVAL-SUMMARY-001` till `-012` är overifierade i praktiken.

**Recommendation:** Antingen (a) definiera en riktig `MeasurementQuality`-enum med medlemmarna `VERIFIED`/`VALID`/`DEGRADED`/`INVALID` som `_classify_quality` faktiskt producerar, och uppdatera kontraktet om det är den avsedda semantiken, eller (b) återanvänd `QualityLevel` och skriv om `_classify_quality` för att mappa mot dess fyra medlemmar (`INVALID/DEGRADED/NOMINAL/HIGH`). Det här är ett designbeslut, inte bara en namnfix.

**Verification test:** `python3 -c "import ka9q_beacon_monitor.model.interval_summary"` ska lyckas; `test_interval_summary.py` ska samlas in och köras.

**Confidence:** 1.0

---

### DM3-F-003 — CRITICAL — StatusSample field contract
**AKB section:** `DM-STATUS-SAMPLE.md` Field Definitions (`pll_locked`, `sequence_number`) · **Python:** `src/ka9q_beacon_monitor/model/status_sample.py` · **Test:** `tests/model/test_status_sample.py`

**Finding:** Kontraktet kräver fälten `pll_locked` (bool/null) och `sequence_number` (int/null, non-negative). Dataklassen har `pll_lock` (fel namn) och saknar `sequence_number` helt.

**Evidence (körd):**
```
TypeError: StatusSample.__init__() got an unexpected keyword argument 'pll_locked'
```
(9/9 tester i `test_status_sample.py` misslyckas med denna eller relaterade orsaker.)

**Impact:** Bryter mot acceptanskriteriet "Every required field... matches this contract" rakt av. Ingen kod i paketet kan konstruera en kontraktsenlig `StatusSample`.

**Recommendation:** Byt `pll_lock` → `pll_locked`; lägg till `sequence_number: int | None = None` med en `>= 0`-kontroll i `__post_init__`.

**Verification test:** `test_status_sample.py::test_valid_sample_is_constructed` och samtliga syskontester.

**Confidence:** 1.0

---

### DM3-F-004 — HIGH — StatusSample enum completeness
**AKB section:** `DM-STATUS-SAMPLE.md` Field Definitions (`demod_mode`, `sample_quality`) · **Python:** `src/ka9q_beacon_monitor/model/status_sample.py`

**Finding:** Kontraktet kräver `demod_mode` ∈ {`linear, fm, am, iq, unknown`} (5 värden); koden har bara `LINEAR, FM` (2). Kontraktet kräver `sample_quality` ∈ {`valid, partial, invalid`}; koden har `VALID, DEGRADED, INVALID` — `DEGRADED` istället för det kontraktsdefinierade `PARTIAL` (som dessutom är en egen definierad term i samma dokuments Definitions-tabell: "Partial sample").

**Evidence:** `class DemodMode(StrEnum): LINEAR = "LINEAR"; FM = "FM"` — saknar AM/IQ/UNKNOWN. `class SampleQuality(StrEnum): VALID; DEGRADED; INVALID` — saknar PARTIAL.

**Impact:** En AM- eller IQ-konfigurerad kanal (vilket `ARCH-KA9Q`s statusfält uttryckligen tillåter) kan inte representeras. "Partial sample"-begreppet, definierat och använt i kontraktets egen prosa, existerar inte i koden.

**Recommendation:** Utöka `DemodMode` med `AM`, `IQ`, `UNKNOWN`; byt `DEGRADED` → `PARTIAL` i `SampleQuality`.

**Verification test:** Ny/utökad enhetstest per tillagt enum-värde.

**Confidence:** 0.9

---

### DM3-F-005 — CRITICAL — StatusSample missing validation
**AKB section:** `DM-STATUS-SAMPLE.md` Failure Modes-tabell, DM-STATUS-SAMPLE-004 · **Python:** `src/ka9q_beacon_monitor/model/status_sample.py` `__post_init__` · **Test:** `tests/model/test_status_sample.py`

**Finding:** Av sju dokumenterade Failure Modes implementerar `__post_init__` bara två (naiv/icke-UTC timestamp, tom `channel_id`). Följande saknas helt:
- Frekvens ≤ 0, NaN eller oändlig → ska avvisas (`test_frequency_must_be_positive`, `test_non_finite_measurement_is_rejected`).
- DM-STATUS-SAMPLE-004: `VALID`-prov måste ha både `baseband_power_db` och `noise_density_db_hz`; `INVALID`-prov får inte ha några mätvärden alls (`test_valid_sample_requires_power_and_noise`, `test_invalid_sample_must_not_expose_measurements`, `test_invalid_sample_without_measurements_is_allowed`).
- Icke-ändliga värden för `gain_db`/`output_level_db`/`headroom_db` avvisas inte.

**Evidence:** Fullständig läsning av `__post_init__` (4 rader kod, 2 kontroller) mot Failure Modes-tabellens 7 rader.

**Impact:** Kontraktets kärnlöfte — "Numeric values SHALL reject NaN and infinity" och kvalitetskonsistensregeln — hålls inte av implementationen. Detta är precis den typ av tyst datakorruption tidigare granskningsrundor (ända från designspecen, F-002/F-003) identifierat som högriskmönster.

**Recommendation:** Implementera samtliga sju regler i `__post_init__`.

**Verification test:** De sex ännu misslyckade testerna i `test_status_sample.py` utöver konstruktions-/immutability-testerna.

**Confidence:** 1.0

---

### DM3-F-006 — HIGH — Test coverage / traceability
**AKB section:** `DM-OBSERVATION.md` `verified_by: TEST-DM-OBSERVATION` · **Python:** `src/ka9q_beacon_monitor/model/observation.py` · **Test:** *(saknas)*

**Finding:** Ingen `tests/model/test_observation.py` finns i paketet, trots att `DM-OBSERVATION.md` deklarerar `verified_by: [TEST-DM-OBSERVATION]` och `Observation` är den mest invariant-täta modellen i paketet (7+ regler i `__post_init__`).

**Evidence:** `find tests -iname "*observation*"` → inga träffar. Enda indirekta konstruktion sker via hjälpfunktioner i `test_interval_summary.py`, som i sin tur inte går att samla in (DM3-F-002) — så `Observation` har för närvarande **noll körda tester** i det här paketet, trots att den (baserat på min manuella läsning) är den mest korrekt implementerade modellen.

**Impact:** Mandatory Review Pass 7 ("every normative rule has at least one executable test") är inte uppfyllt för `DM-OBSERVATION-001` till `-010`.

**Recommendation:** Lägg till `tests/model/test_observation.py` med direkt, oberoende täckning av varje `DM-OBSERVATION-*`-regel.

**Verification test:** Den nya filens existens och gröna körning.

**Confidence:** 0.95

---

### DM3-F-007 — MEDIUM — Code-to-contract gap
**AKB section:** `DM-INTERVAL-SUMMARY.md` (DM-INTERVAL-SUMMARY-006/007) · **Python:** `interval_summary.py` `_classify_summary`

**Finding:** Koden avgör `final_state` med en deterministisk if/elif-kedja där täckningsvillkoret (`< 20%` → `NO_DATA`) prövas *före* interferensvillkoret (`> 50%` → `INTERFERED`) — vilket korrekt löser den prioritetsfråga tidigare granskningsrundor flaggade (motsvarande gammal "AI-013"/M2-liknande ambiguity). Men kontraktet självt listar de två reglerna som separata punkter utan att ange evalueringsordning.

**Evidence:** `_classify_summary`: `if coverage < minimum...: return NO_DATA` prövas innan `if interference_count/valid_count > 0.5: return INTERFERED`.

**Impact:** Litet — koden gör rätt sak, men en framtida omimplementation utan tillgång till just den här koden skulle kunna göra fel, eftersom kontraktstexten inte kräver den ordningen.

**Recommendation:** Lägg till en mening i `DM-INTERVAL-SUMMARY.md`: "Rules DM-INTERVAL-SUMMARY-006 through -010 are evaluated in listed order; first match wins."

**Verification test:** N/A — dokumentationsåtgärd.

**Confidence:** 0.8

---

### DM3-F-008 — LOW — Cross-model consistency
**AKB section:** N/A (implementationsdetalj, ingen kontraktstext styr casing) · **Python:** `observation.py` (`DetectionState`), `interval_summary.py` (`SummaryState`)

**Finding:** `DetectionState`s strängvärden är gemener (`"no_signal"`, `"probable_beacon"`, ...) medan `SummaryState`s är versaler (`"NO_DATA"`, `"STRONG"`, ...) — två syskonenums i samma modell-lager med olika case-konvention.

**Impact:** Kosmetiskt, men riskerar förvirring i API-svar/loggar där båda förekommer sida vid sida.

**Recommendation:** Standardisera på en konvention (troligen versaler, för konsekvens med databasens `TEXT`-kolumner och `SummaryState`).

**Confidence:** 0.6

---

### DM3-F-009 — QUESTION — Overall test-suite health
**Finding:** Av 39 deklarerade tester (`test_database_model.py`: 4, `test_status_sample.py`: 9, `test_schema.py`: 6, `test_interval_summary.py`: 10, `test_measurement_window.py`: 10) körs och passerar bara 10 (4+6). 9 misslyckas. 20 exekveras aldrig alls.

**Evidence:** Egen körning, se sammanfattningen ovan.

**Impact:** Det här är inte ett enskilt fynd utan en sammanfattande kvalitetssignal — täckningsgraden som faktiskt bevisligen fungerar är ~26%, inte de ~100% en läsning av enbart filnamnen skulle antyda.

**Recommendation:** Efter att DM3-F-001 till -006 är åtgärdade, kör om hela sviten och bekräfta 39/39 gröna innan nästa granskningsrunda.

**Confidence:** 1.0

## 4. Contract/Code Coverage Matrix

| DM Contract | Fält/enum matchar | Valideringsregler implementerade | Tester körbara | Tester gröna |
|---|---|---|---|---|
| DM-STATUS-SAMPLE | Nej (2 fel, 2 ofullständiga enums) | 2/7 | Ja | 0/9 |
| DM-MEASUREMENT-WINDOW | Ja (manuell läsning) | Ja (manuell läsning) | **Nej** (blockerad av DM3-F-001) | 0/10 (oexekverade) |
| DM-OBSERVATION | Ja (manuell läsning) | Ja (manuell läsning) | N/A — ingen testfil | 0/0 |
| DM-INTERVAL-SUMMARY | Nej (`MeasurementQuality` saknas) | Delvis (manuell läsning av det som går att läsa) | **Nej** (modul går inte att importera) | 0/10 (oexekverade) |
| DM-DATABASE | Ja | Ja | Ja | 6/6 |

## 5. Requirements Traceability Gaps

- `DM-OBSERVATION` → `TEST-DM-OBSERVATION`: testfilen existerar inte (DM3-F-006).
- `DM-INTERVAL-SUMMARY` → `quality: MeasurementQuality`: typen som kontraktet kräver existerar inte i koden (DM3-F-002).
- `DM-STATUS-SAMPLE` → `pll_locked`, `sequence_number`: fält som kontraktet kräver saknas/är felnamngivna i koden (DM3-F-003).

## 6. Unverified Assumptions

- Om `MeasurementQuality` är tänkt att vara en helt ny enum eller ett alias för `QualityLevel` är ett designbeslut jag inte kan fatta åt er (DM3-F-002) — flaggat som NEEDS_VERIFICATION/domänbeslut.
- Jag har inte verifierat `MeasurementWindow` eller `Observation` genom körning (bara manuell läsning), eftersom testsviten inte kan köra dem. Min bedömning att de är korrekta är därför lägre-confidence än de fynd jag faktiskt körde och reproducerade.

## 7. Recommended Edits

1. Fixa `model/__init__.py` att exportera hela den publika ytan (DM3-F-001).
2. Lös `MeasurementQuality`-frågan — antingen skapa typen eller mappa om till `QualityLevel` (DM3-F-002).
3. Fixa `StatusSample`: `pll_locked`-namn, `sequence_number`-fält, `DemodMode`/`SampleQuality`-enums, samtliga sju valideringsregler (DM3-F-003, -004, -005).
4. Lägg till `tests/model/test_observation.py` (DM3-F-006).
5. Lägg till explicit evalueringsordning i `DM-INTERVAL-SUMMARY.md` (DM3-F-007).
6. Standardisera enum-strängcasing (DM3-F-008).
7. Kör om hela sviten och bekräfta 39/39 gröna (DM3-F-009).

## 8. JSON Summary

```json
{
  "review_summary": {
    "decision": "RE_REVIEW_REQUIRED",
    "confidence": 0.95,
    "executed_test_results": {"declared": 39, "passed": 10, "failed": 9, "not_collected": 20},
    "top_risks": [
      "model/__init__.py exports only 2 of 12 public symbols, blocking 20 tests from collection (DM3-F-001)",
      "interval_summary.py imports a MeasurementQuality type that does not exist anywhere in the codebase (DM3-F-002)",
      "StatusSample has a renamed field, a missing field, two incomplete enums, and 5 of 7 undocumented-yet-required validations missing (DM3-F-003/004/005)"
    ]
  },
  "findings": [
    {"id": "DM3-F-001", "severity": "CRITICAL", "category": "Package structure", "akb_section": "N/A", "python_location": "src/ka9q_beacon_monitor/model/__init__.py", "test_location": "tests/model/test_interval_summary.py, tests/model/test_measurement_window.py", "finding": "__init__.py exports only DatabaseConfig and RetentionPolicy; ten other public model symbols are missing.", "evidence": "pytest collection fails with ImportError for DetectionState and DemodMode from ka9q_beacon_monitor.model.", "impact": "20 of 39 declared tests never execute.", "recommendation": "Re-export the full public model surface from __init__.py.", "verification_test": "pytest -q shows 0 collection errors.", "confidence": 1.0},
    {"id": "DM3-F-002", "severity": "CRITICAL", "category": "Data model", "akb_section": "DM-INTERVAL-SUMMARY.md Interfaces (quality: MeasurementQuality)", "python_location": "src/ka9q_beacon_monitor/model/interval_summary.py:10, _classify_quality", "test_location": "tests/model/test_interval_summary.py", "finding": "interval_summary.py imports MeasurementQuality from observation.py, which does not define it; no such type exists anywhere in the codebase, and _classify_quality's return values do not match QualityLevel's actual members either.", "evidence": "Direct import of ka9q_beacon_monitor.model.interval_summary raises ImportError independent of DM3-F-001.", "impact": "The entire IntervalSummary module, including all aggregation and threshold logic, has never been executed.", "recommendation": "Either define a MeasurementQuality enum matching _classify_quality's outputs, or rewrite _classify_quality to use QualityLevel.", "verification_test": "Direct import succeeds; test_interval_summary.py collects and runs.", "confidence": 1.0},
    {"id": "DM3-F-003", "severity": "CRITICAL", "category": "Data model", "akb_section": "DM-STATUS-SAMPLE.md Field Definitions", "python_location": "src/ka9q_beacon_monitor/model/status_sample.py", "test_location": "tests/model/test_status_sample.py", "finding": "Contract field pll_locked is named pll_lock in code; contract field sequence_number is entirely absent from the dataclass.", "evidence": "TypeError: StatusSample.__init__() got an unexpected keyword argument 'pll_locked'; all 9 tests in test_status_sample.py fail.", "impact": "No code in the package can construct a contract-conformant StatusSample.", "recommendation": "Rename pll_lock to pll_locked; add sequence_number: int | None with a non-negative check.", "verification_test": "test_status_sample.py::test_valid_sample_is_constructed and siblings.", "confidence": 1.0},
    {"id": "DM3-F-004", "severity": "HIGH", "category": "Data model", "akb_section": "DM-STATUS-SAMPLE.md Field Definitions (demod_mode, sample_quality)", "python_location": "src/ka9q_beacon_monitor/model/status_sample.py", "test_location": "tests/model/test_status_sample.py", "finding": "DemodMode is missing AM/IQ/UNKNOWN (contract requires 5 values, code has 2); SampleQuality uses DEGRADED instead of the contract's PARTIAL.", "evidence": "class DemodMode(StrEnum): LINEAR, FM only; class SampleQuality(StrEnum): VALID, DEGRADED, INVALID.", "impact": "AM/IQ-configured channels cannot be represented; the contract's own 'Partial sample' term has no code representation.", "recommendation": "Extend DemodMode with AM, IQ, UNKNOWN; rename DEGRADED to PARTIAL in SampleQuality.", "verification_test": "New unit tests per added enum value.", "confidence": 0.9},
    {"id": "DM3-F-005", "severity": "CRITICAL", "category": "Data model", "akb_section": "DM-STATUS-SAMPLE.md Failure Modes, DM-STATUS-SAMPLE-004", "python_location": "src/ka9q_beacon_monitor/model/status_sample.py __post_init__", "test_location": "tests/model/test_status_sample.py", "finding": "Only 2 of 7 documented failure-mode validations are implemented; frequency positivity, NaN/infinity rejection, and the VALID/INVALID quality-consistency rule are entirely missing.", "evidence": "__post_init__ contains only timestamp and channel_id checks.", "impact": "The contract's core data-integrity guarantees are not enforced by the implementation.", "recommendation": "Implement all seven documented rules in __post_init__.", "verification_test": "The six still-failing validation tests in test_status_sample.py.", "confidence": 1.0},
    {"id": "DM3-F-006", "severity": "HIGH", "category": "Test coverage", "akb_section": "DM-OBSERVATION.md verified_by: TEST-DM-OBSERVATION", "python_location": "src/ka9q_beacon_monitor/model/observation.py", "test_location": "(missing) tests/model/test_observation.py", "finding": "No dedicated test file exists for Observation despite it being declared as verified_by TEST-DM-OBSERVATION and having 7+ enforced invariants.", "evidence": "find tests -iname '*observation*' returns nothing; Observation is only indirectly constructed inside the uncollectable test_interval_summary.py.", "impact": "Zero executed test coverage for Observation despite it being the most invariant-dense model in the package.", "recommendation": "Add tests/model/test_observation.py with direct coverage of each DM-OBSERVATION-* rule.", "verification_test": "New file exists and passes.", "confidence": 0.95},
    {"id": "DM3-F-007", "severity": "MEDIUM", "category": "Traceability", "akb_section": "DM-INTERVAL-SUMMARY.md (DM-INTERVAL-SUMMARY-006/007)", "python_location": "src/ka9q_beacon_monitor/model/interval_summary.py _classify_summary", "test_location": "N/A", "finding": "Code correctly evaluates coverage before interference (first-match-wins), resolving a historical ambiguity, but the contract does not state this evaluation order.", "evidence": "_classify_summary checks coverage before interference_count/valid_count.", "impact": "Minor - code is correct but a future reimplementation without this code as reference could get it wrong.", "recommendation": "Add an explicit evaluation-order sentence to DM-INTERVAL-SUMMARY.md.", "verification_test": "N/A - documentation.", "confidence": 0.8},
    {"id": "DM3-F-008", "severity": "LOW", "category": "Consistency", "akb_section": "N/A", "python_location": "observation.py DetectionState, interval_summary.py SummaryState", "test_location": "N/A", "finding": "DetectionState values are lowercase strings while SummaryState values are uppercase, an inconsistent convention between sibling enums.", "evidence": "DetectionState.NO_SIGNAL = 'no_signal' vs SummaryState.NO_DATA = 'NO_DATA'.", "impact": "Cosmetic, risks confusion in API responses/logs.", "recommendation": "Standardize casing across model-layer enums.", "verification_test": "N/A.", "confidence": 0.6},
    {"id": "DM3-F-009", "severity": "QUESTION", "category": "Test coverage", "akb_section": "N/A", "python_location": "N/A", "test_location": "tests/", "finding": "Of 39 declared tests, only 10 pass when actually run; 9 fail and 20 never execute.", "evidence": "Own pytest run, see executive summary.", "impact": "Actual proven coverage is ~26%, not the ~100% file-name inspection alone would suggest.", "recommendation": "Re-run the full suite and confirm 39/39 green after DM3-F-001 through -006 are fixed.", "verification_test": "N/A.", "confidence": 1.0}
  ],
  "coverage_matrix": [
    {"contract": "DM-STATUS-SAMPLE", "fields_match": false, "validations_implemented": "2/7", "tests_collectable": true, "tests_passing": "0/9"},
    {"contract": "DM-MEASUREMENT-WINDOW", "fields_match": true, "validations_implemented": "manual review only", "tests_collectable": false, "tests_passing": "0/10"},
    {"contract": "DM-OBSERVATION", "fields_match": true, "validations_implemented": "manual review only", "tests_collectable": "N/A - no test file", "tests_passing": "0/0"},
    {"contract": "DM-INTERVAL-SUMMARY", "fields_match": false, "validations_implemented": "partial, manual review only", "tests_collectable": false, "tests_passing": "0/10"},
    {"contract": "DM-DATABASE", "fields_match": true, "validations_implemented": "verified", "tests_collectable": true, "tests_passing": "6/6"}
  ],
  "requirements_traceability_gaps": [
    "DM-OBSERVATION's declared TEST-DM-OBSERVATION does not exist as a file (DM3-F-006).",
    "DM-INTERVAL-SUMMARY's quality: MeasurementQuality field type is not implemented anywhere (DM3-F-002).",
    "DM-STATUS-SAMPLE's pll_locked and sequence_number fields are missing/misnamed in code (DM3-F-003)."
  ],
  "unverified_assumptions": [
    "Whether MeasurementQuality is intended as a new enum or an alias for QualityLevel is a domain decision, not something I can resolve (DM3-F-002).",
    "MeasurementWindow and Observation correctness is based on manual contract-to-code reading only, since the test suite cannot execute them; confidence is lower than for findings I directly reproduced by running code."
  ],
  "recommended_edits": [
    "Fix model/__init__.py exports (DM3-F-001).",
    "Resolve the MeasurementQuality type gap (DM3-F-002).",
    "Fix StatusSample field names, missing field, enums, and validation logic (DM3-F-003/004/005).",
    "Add tests/model/test_observation.py (DM3-F-006).",
    "Document IntervalSummary's rule evaluation order (DM3-F-007).",
    "Standardize enum string casing (DM3-F-008).",
    "Re-run full suite for 39/39 green (DM3-F-009)."
  ]
}
```
