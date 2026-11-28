"""Six authored source lineages for independent excerpt confirmation."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from textwrap import dedent


@dataclass(frozen=True)
class Span:
    path: str
    first: int
    last: int
    documentation: bool


@dataclass(frozen=True)
class Case:
    repository: str
    name: str
    family: str
    prompt: str
    required: tuple[Span, ...]


def source(*sections, long=False):
    """Use an explicit long/short annotation so materialization has no query inputs."""
    return long, sections


def docs(label, text):
    return label, text, True


def code(label, text):
    return label, text, False


def build_file(path, fixture):
    long, sections = fixture
    suffix = PurePosixPath(path).suffix
    comment = "#" if suffix in {".py", ".rb"} else "//"
    lines, spans = [], {}
    for index, (label, text, is_documentation) in enumerate(sections):
        if index and long:
            # Fill the gap with source comments or handbook records. Sections
            # cannot accidentally share one 12 KiB evidence window.
            lines.extend(
                f"{'' if suffix == '.md' else comment + ' '}Historical maintenance entry {i:03d}: "
                "superseded material retained with its original numbering."
                for i in range(180)
            )
        block = dedent(text).strip("\n").splitlines()
        spans[label] = Span(path, len(lines) + 1, len(lines) + len(block), is_documentation)
        lines.extend(block)
        lines.append("")
    return "\n".join(lines), spans


LINEAGES = {
    "cold-chain": (
        {
            "app/Logistics/ShipmentProbe.php": source(
                code("preamble", "<?php\nnamespace App\\Logistics;"),
                code("alert-display", """
                    function formatTemperatureAlert(float $temperature, string $warehouse): string {
                        return sprintf('%s display temperature %.1f', $warehouse, $temperature);
                    }
                """),
                code("excursion", """
                    function temperatureExcursionMinutes(array $readings, float $ovenLimit): int {
                        return array_sum(array_column(array_filter(
                            $readings, fn ($reading) => $reading['temperature'] > $ovenLimit
                        ), 'minutes'));
                    }
                """),
                docs("handover", """
                    // For a manual handover after a sealed case warms up, copy the
                    // original temperature excursion log into the carrier ledger.
                """),
                long=True,
            ),
            "handbook/dispatch.md": source(
                docs("audit", "### Audit forms\nLog every carrier change on the daily route sheet."),
                docs("quarantine", """
                    ### Broken seal
                    A broken seal goes into quarantine, even when the refrigeration log is complete.
                """),
                docs("sensor", "### Sensor pairing\nA spare handset pairs over the dispatch console."),
                long=True,
            ),
            "app/Logistics/RouteTag.php": source(code("tag", """
                <?php
                const CARRIER_ROUTE_TAG = 'load-route';
            """)),
            "app/Logistics/DepotLabel.php": source(code("depot", """
                <?php
                function depotLabel(string $warehouse): string { return strtolower($warehouse); }
            """)),
        },
        (
            ("excursion-minutes", "implementation", "Where are minutes summed during a temperature excursion above the limit?", ("excursion",)),
            ("broken-seal", "documentation", "What does dispatch require after receiving a case with a broken seal?", ("quarantine",)),
            ("carrier-handover", "mixed", "For a carrier handover after warming, find how a temperature excursion is measured and where its original log goes.", ("excursion", "handover")),
            ("route-tag", "short", "Find the constant for the carrier route tag.", ("tag",)),
        ),
    ),
    "harbor-clearance": (
        {
            "internal/berth/window.go": source(
                code("package", "package berth"),
                code("draft-display", "func displayedDraft(centimetres int) float64 { return float64(centimetres) / 100 }"),
                code("tidal", """
                    func tidalDraftAllowance(depth, keelClearance, swellMargin int) int {
                        return max(0, depth-keelClearance-swellMargin)
                    }
                """),
                long=True,
            ),
            "operator/clearance.md": source(
                docs("morning", "### Morning desk\nThe safety checklist is signed at shift start."),
                docs("tug", """
                    ### Tug handoff
                    If the berth has less than six metres of clearance, ask the harbour tug to hold at the outer marker.
                """),
                docs("permit", "### Permit desk\nAn inbound vessel must carry its clearance permit number."),
                long=True,
            ),
            "internal/berth/retry.go": source(code("retry", """
                package berth
                const ClearanceRetrySeconds = 45
            """)),
            "internal/report/depth.go": source(code("report", """
                package report
                var ColumnName = "recorded depth"
            """)),
        },
        (
            ("tidal-allowance", "implementation", "Locate the tidal draft allowance after deducting swell and keel clearance.", ("tidal",)),
            ("permit-number", "documentation", "Which clearance permit detail must each inbound vessel carry?", ("permit",)),
            ("tug-clearance", "mixed", "Find the depth and clearance calculation and the documented tug handoff for insufficient berth clearance.", ("tidal", "tug")),
            ("retry-constant", "short", "Where does the clearance retry interval in seconds come from?", ("retry",)),
        ),
    ),
    "caption-relay": (
        {
            "src/caption/segments.py": source(
                code("seconds", "def displayed_seconds(frames, rate): return frames / rate"),
                code("coalesce", """
                    def coalesce_overlapping_cues(cues):
                        ordered = sorted(cues, key=lambda cue: cue.start)
                        return [cue for i, cue in enumerate(ordered) if not i or cue.end > ordered[i - 1].end]
                """),
                docs("recovery", """
                    # During websocket recovery, start at the last acknowledged sequence.
                    # The acknowledgement belongs to the caption relay, never to the display client.
                """),
                code("acknowledged", "def acknowledged_caption_sequence(client): return client.sequence"),
                long=True,
            ),
            "operator/live_captioning.md": source(
                docs("shift", "### Shift notes\nReport a relay handoff in the shared queue."),
                docs("names", """
                    ### Names in captions
                    For a corrected name, replay the last cue and label it as a correction in the operator console.
                """),
                long=True,
            ),
            "src/caption/encoding.py": source(code("bom", "DEFAULT_CAPTION_ENCODING = 'utf-8-sig'")),
            "src/caption/snapshot.py": source(code("snapshot", "def snapshot(cues): return tuple(cues)")),
        },
        (
            ("overlapping-cues", "implementation", "Where are overlapping caption cues coalesced after being sorted?", ("coalesce",)),
            ("recovery-sequence", "documentation", "During websocket recovery, which acknowledged caption sequence does the relay resume from?", ("recovery",)),
            ("caption-correction", "mixed", "Find the cue overlap handling and the captioning procedure for replaying a corrected cue name.", ("coalesce", "names")),
            ("caption-encoding", "short", "Locate the default caption encoding.", ("bom",)),
        ),
    ),
    "alloy-lab": (
        {
            "src/assay/thresholds.rs": source(
                code("calibration-style", """
                    pub fn displayCalibrationExpiration(labels: &[&str]) -> usize { labels.len() }
                """),
                code("allowance", """
                    pub fn slag_allowance(batch_mass: u32, melt_grade: u32) -> u32 {
                        batch_mass.saturating_mul(melt_grade).div_ceil(100)
                    }
                """),
                docs("expiration", """
                    // Calibration expiration is recorded from the reference coupon date,
                    // not from the day an assay operator uploads a label.
                """),
                long=True,
            ),
            "manual/quality.md": source(
                docs("intro", "### Daily inspection\nThe shift lead reviews tooling notes."),
                docs("release", """
                    ### Assay release
                    A second operator must sign the slag assay before the batch may be marked ready.
                """),
                long=True,
            ),
            "src/assay/code.rs": source(code("stamp", "pub const ASSAY_STAMP_PREFIX: &str = \"ALY\";")),
            "src/assay/display.rs": source(code("display", "pub fn batch_label(id: u32) -> String { format!(\"{id:08}\") }")),
        },
        (
            ("slag-allowance", "implementation", "How does batch mass and melt grade determine slag allowance?", ("allowance",)),
            ("calibration-expiration", "documentation", "Which date counts for a calibration expiration label?", ("expiration",)),
            ("slag-release", "mixed", "Find the slag allowance calculation and the assay release rule before marking a batch ready.", ("allowance", "release")),
            ("assay-stamp", "short", "Find the assay stamp prefix.", ("stamp",)),
        ),
    ),
    "seed-library": (
        {
            "lib/seed_library/checkouts.rb": source(
                code("decoy", "def display_reservation_barcode(code); code.to_s; end"),
                code("renew", """
                    def extend_seed_loan(loan, calendar)
                      return loan if loan.returned?
                      loan.with_due(calendar.next_open_day(loan.due + 14))
                    end
                """),
                docs("hold", """
                    # A donated packet with an unknown harvest year may be held
                    # for a seed exchange only after a volunteer enters the species.
                """),
                code("barcodes", """
                    def normalize_reservation_barcode(raw)
                      raw.to_s.strip.upcase.delete('-')
                    end
                """),
                long=True,
            ),
            "handbook/volunteer.md": source(
                docs("visitor", "### Visitor hours\nA station opens when a volunteer checks in."),
                docs("donation", """
                    ### Donation receipts
                    Do not publish a donor's phone number on a receipt posted by the seed station.
                """),
                long=True,
            ),
            "lib/seed_library/catalog.rb": source(code("catalog", "CATALOG_VERSION = 3")),
        },
        (
            ("extend-loan", "implementation", "Find the seed loan extension and how the calendar chooses the new due date.", ("renew",)),
            ("reservation-barcode", "implementation", "Where is a reservation barcode normalized to uppercase and stripped?", ("barcodes",)),
            ("unknown-harvest", "documentation", "Can an unknown harvest year packet be held for a seed exchange?", ("hold",)),
            ("donor-receipt", "documentation", "Which donor contact detail must stay off a posted donation receipt?", ("donation",)),
        ),
    ),
    "field-census": (
        {
            "src/observations/survey.ts": source(
                code("preview", "export function formatObserverApproximation(raw: number) { return raw.toFixed(2); }"),
                code("duplicates", """
                    export function mergeDuplicateSightings(first: Sighting, second: Sighting): Sighting {
                      if (first.observer !== second.observer) return first;
                      return first.confidence >= second.confidence ? first : second;
                    }
                """),
                docs("coordinates", """
                    // For a protected nest, record an approximate coordinate rounded
                    // outward to the enclosing grid cell before the sighting leaves the team.
                """),
                code("census", """
                    export function surveyEffortMinutes(start: Date, finish: Date, paused: number): number {
                      return Math.max(0, (finish.getTime() - start.getTime()) / 60000 - paused);
                    }
                """),
                long=True,
            ),
            "field/operations.md": source(
                docs("startup", "### Transect setup\nCheck the battery before leaving the station."),
                docs("rain", """
                    ### Rain stoppage
                    Start a new transect after rain forces observers out for more than forty minutes.
                """),
                long=True,
            ),
            "src/observations/batch.ts": source(code("batch", "export const packetCapacity = 32;")),
        },
        (
            ("duplicate-sightings", "implementation", "Which sighting wins when an observer records duplicate entries with different confidence?", ("duplicates",)),
            ("effort-minutes", "implementation", "Where does the effort calculation subtract paused minutes from the survey duration?", ("census",)),
            ("protected-coordinate", "documentation", "How should a protected nest coordinate be approximated before sharing the sighting?", ("coordinates",)),
            ("rain-transect", "documentation", "When does a rain stoppage require a new transect?", ("rain",)),
        ),
    ),
}


def fixtures():
    for repository, (files, tasks) in LINEAGES.items():
        sources, annotations = {}, {}
        for path, source_fixture in files.items():
            sources[path], spans = build_file(path, source_fixture)
            if annotations.keys() & spans.keys():
                raise ValueError(f"Duplicate source annotation in {repository}")
            annotations.update(spans)
        cases = [
            Case(repository, name, family, prompt, tuple(annotations[key] for key in targets))
            for name, family, prompt, targets in tasks
        ]
        yield repository, sources, cases
