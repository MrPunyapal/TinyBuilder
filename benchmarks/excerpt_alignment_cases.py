"""Frozen model-free development cases for excerpt alignment."""


# Labels are scorer-only. Each marker labels a unique complete source line.
# The late identifier is at least one full excerpt budget from early decoys.
CASES = (
    ("camel", "limits.rs", "Locate reservoir pressure compensation.", "reservoirPressureCompensation",
     "pub fn reservoirPressureCompensation() -> i32 { 8 }", "fn reservoir() {}"),
    ("screaming-snake", "configuration.php", "Locate the evacuation aisle override.", "EVACUATION_AISLE_OVERRIDE",
     "    const EVACUATION_AISLE_OVERRIDE = 4;", "    const override = 0;"),
    ("plural", "upload.py", "Locate archival categories for media assets.", "archival_category",
     "def archival_category(media_assets): return media_assets[0]", "def archival(): return None"),
    ("verb", "clock.rs", "Find synchronizing clock records.", "synchronized_clock_record",
     "pub fn synchronized_clock_record() {}", "pub fn clock() {}"),
    ("competing", "transit.php", "Find the continental surcharge exemption.", "ContinentalSurchargeExemption",
     "final class ContinentalSurchargeExemption {}", "// continental and surchargeable routes"),
    ("four-term-cutoff", "scanner.py", "Find billing id allocation for internationalized character representation.",
     "allocateBillingID", "def allocateBillingID(): return 3", "# internationalized character representation"),
    ("mixed-case", "registry.rs", "Find glacier sampling retry.", "GLACIER_samplingRetry",
     "pub fn GLACIER_samplingRetry() {}", "pub fn retry() {}"),
    ("deeper-anchor", "mapping.py", "Locate tributary watershed registration.", "tributaryWatershedRegistration",
     "def tributaryWatershedRegistration(): return 1", "def tributary(): return 0"),
    ("short-file", "palette.py", "Find palette override.", "palette_override",
     "def palette_override(): return 'blue'", ""),
    ("short-cross-file", "billing.php", "Find freight quote transmittal.", "freightQuoteTransmittal",
     "function freightQuoteTransmittal() { return 0; }", ""),
)


def fixtures():
    for case, filename, prompt, marker, target, decoy in CASES:
        lines = []
        if decoy:
            lines = [decoy] + ["// archived handbook reference entry with neutral vocabulary"] * 676
            if case == "deeper-anchor":
                lines += ["// watershed"] + ["// independent historical reference entry"] * 476
        lines.append(target)
        expected_line = len(lines)
        if decoy:
            lines += ["// archived secondary reference entry with neutral vocabulary"] * 240
        if filename.endswith(".php"):
            lines.insert(0, "<?php")
            expected_line += 1
        sources = {filename: "\n".join(lines) + "\n",
                   "notes.txt": "Reviewed overview of the module.\n"}
        if case == "short-cross-file":
            sources["worker.php"] = "<?php\nfunction sendFreightQuote() {}\n"
        assert sources[filename].splitlines()[expected_line - 1].count(marker) == 1
        yield case, prompt, filename, expected_line, sources
