"""Evaluator-only prompts and required source evidence for confirmation v1."""

from .retrieval_confirmation import REPOSITORIES


# A bare path requires the complete file. A (path, marker) pair requires the
# one line containing that unique mark, even when only an excerpt is delivered.
TASKS = {
    "theatre": (
        ("hold-path", "Trace what happens from submitting a reservation to creating its temporary seat hold.",
         "routes/web.php", "app/Http/Controllers/ReservationController.php", "app/Services/Seating/SeatAllocator.php"),
        ("accessibility", "Where is the wheelchair field required when patrons place a hold?",
         "app/Http/Requests/HoldRequest.php"),
        ("permission", "Find the permission check for cancelling a reservation from a different venue.",
         "app/Policies/ReservationPolicy.php"),
        ("sweep", "Trace the scheduled cleanup of unpaid holds whose expiry already passed.",
         "routes/console.php", "app/Jobs/ExpireHolds.php"),
        ("ticket-time", "Where is the admission ticket timestamp rendered and converted to local time?",
         "resources/views/reservations/ticket.blade.php"),
        ("fingerprint", "Find where the contact hash is indexed and where it can be mass assigned.",
         "database/migrations/2026_02_01_000000_add_contact_hash.php", "app/Models/Reservation.php"),
        ("zone", "Where is the venue timezone default configured?",
         "config/venue.php"),
        ("charge-count", "Which SeatAllocator determines how many seats appear on an invoice?",
         "app/Services/Billing/SeatAllocator.php"),
        ("aisle", "Find the legacy rule defining the evacuation aisle number.",
         ("app/Support/Legacy/HouseRules.php", "public const EVACUATION_AISLE")),
        ("public-link", "Where is a public ticket link required to carry a signature?",
         "routes/web.php"),
        ("no-scanning", "Find the barcode scanner calibration and camera device discovery."),
        ("no-waitlist", "Find how customers progress from the automated waitlist into vacant seats."),
    ),
    "observatory": (
        ("checksum", "Trace how a corrupted telemetry packet is rejected and where its checksum is calculated.",
         "src/observatory/pipeline/decoder.py", "src/observatory/protocol/crc.py"),
        ("retention", "Where are historical readings deleted and their age cutoff computed?",
         "src/observatory/storage/sqlite.py", "src/observatory/storage/retention.py"),
        ("suppression", "Trace how repeated alerts are suppressed before the transport publishes a notice.",
         "src/observatory/alerts/dedup.py", "src/observatory/alerts/routing.py"),
        ("lease", "Where does renewing the gateway lease reject an expired owner?",
         "src/observatory/gateway/lease.py"),
        ("args", "Find the command line flag controlling the sampling interval.",
         "src/observatory/cli/options.py"),
        ("presentation", "Where are display units and compact interval formatting selected?",
         "src/observatory/render/options.py"),
        ("speed", "Locate the conversion of wind velocity into kilometres per hour.",
         "src/observatory/units/wind.py"),
        ("region", "Find the aurora region lookup inside the archival region catalog.",
         ("src/observatory/catalog/codes.py", "def aurora_region(code)")),
        ("crc", "Find crc16.",
         "src/observatory/protocol/crc.py"),
        ("threshold", "Where do we assign the 72 hour default duration for retaining readings?",
         "src/observatory/storage/retention.py"),
        ("no-acoustic", "Find how the microphone resampler removes acoustic echoes."),
        ("no-database-retry", "Find the retry backoff used when the SQLite database is locked."),
    ),
    "dispatch": (
        ("frame", "Trace packet reception and find the maximum size of a decoded frame.",
         "src/net/listener.rs", "src/protocol/frame.rs"),
        ("order", "Find the task sorting logic and the queue rule used to break ties between equal deadlines.",
         "src/worker/scheduler.rs", "src/queues/priority.rs"),
        ("principal", "Which lease validity check is for security credentials rather than cache age?",
         "src/security/lease.rs"),
        ("stale-cache", "Where is the refresh period compared against the age of a cached value?",
         "src/cache/lease.rs"),
        ("flush", "Find the durable journal append operation that flushes the writer.",
         "src/state/journal.rs"),
        ("retry", "Trace reconnect delay computation and where the base delay and retry count are set.",
         "src/net/reconnect.rs", "src/config/defaults.rs"),
        ("rx", "Where are RX and TX gauges named?",
         "src/telemetry/metrics.rs"),
        ("escape", "Find the function that escapes a delimiter in the codec.",
         ("src/codec/escape.rs", "pub fn escape_delimiter")),
        ("bounds", "Locate the logic responsible for discarding truncated frames.",
         "src/protocol/frame.rs"),
        ("cap", "Where is the initial reconnect time configured?",
         "src/config/defaults.rs"),
        ("no-sharding", "Find the consistent hashing ring rebalance algorithm."),
        ("no-encryption", "Find how encryption keys are rotated before reconnecting."),
    ),
}


def cases():
    for repo, tasks in TASKS.items():
        for task, prompt, *targets in tasks:
            required = {}
            for target in targets:
                if isinstance(target, str):
                    path = target
                    REPOSITORIES[repo][path]
                    required[path] = None
                else:
                    path, marker = target
                    lines = REPOSITORIES[repo][path].splitlines()
                    matches = [number for number, line in enumerate(lines, 1) if marker in line]
                    if len(matches) != 1:
                        raise ValueError(f"Expected one source marker for {repo}/{task}")
                    required[path] = matches[0]
            yield repo, task, prompt, required
