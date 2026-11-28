"""Frozen public source-only confirmation corpus. Fixtures are never executed."""

from hashlib import sha256
import json
from pathlib import Path

from .retrieval_laravel_fixtures import LARAVEL_PROJECTS


def _laravel_file(namespace, body, imports=()):
    uses = "".join(f"use {name};\n" for name in imports)
    return f"<?php\n\nnamespace App\\{namespace};\n\n{uses}\n{body}\n"


LARAVEL = {
    "routes/web.php": r"""<?php
use App\Http\Controllers\ReservationController;
use Illuminate\Support\Facades\Route;
Route::post('/reservations', [ReservationController::class, 'store'])->middleware('auth');
Route::get('/reservations/{reservation}', [ReservationController::class, 'show'])->middleware('signed');
""",
    "app/Http/Controllers/ReservationController.php": _laravel_file(
        "Http\\Controllers", """final class ReservationController
{
    public function store(HoldRequest $request, SeatAllocator $allocator)
    {
        return response()->json($allocator->hold($request->validated()), 202);
    }
    public function show(Reservation $reservation)
    {
        return view('reservations.ticket', ['reservation' => $reservation]);
    }
}""", ("App\\Http\\Requests\\HoldRequest", "App\\Services\\Seating\\SeatAllocator", "App\\Models\\Reservation")),
    "app/Http/Requests/HoldRequest.php": _laravel_file(
        "Http\\Requests", """final class HoldRequest extends FormRequest
{
    public function rules(): array
    {
        return ['wheelchair' => ['required', 'boolean'], 'patrons' => ['required', 'integer', 'min:1']];
    }
}""", ("Illuminate\\Foundation\\Http\\FormRequest",)),
    "app/Services/Seating/SeatAllocator.php": _laravel_file(
        "Services\\Seating", """final class SeatAllocator
{
    public function hold(array $input)
    {
        return Reservation::create(['count' => $input['patrons'], 'expires_at' => now()->addMinutes(8)]);
    }
}""", ("App\\Models\\Reservation",)),
    "app/Models/Reservation.php": _laravel_file(
        "Models", """final class Reservation extends Model
{
    protected $fillable = ['count', 'expires_at', 'contact_hash'];
    protected $casts = ['expires_at' => 'datetime'];
}""", ("Illuminate\\Database\\Eloquent\\Model",)),
    "app/Policies/ReservationPolicy.php": _laravel_file(
        "Policies", """final class ReservationPolicy
{
    public function cancel(User $actor, Reservation $reservation): bool
    {
        return $actor->venue_id === $reservation->venue_id && $actor->can_refund;
    }
}""", ("App\\Models\\User", "App\\Models\\Reservation")),
    "app/Jobs/ExpireHolds.php": _laravel_file(
        "Jobs", """final class ExpireHolds implements ShouldQueue
{
    public function handle(): void
    {
        Reservation::whereNull('paid_at')->where('expires_at', '<', now())->delete();
    }
}""", ("App\\Models\\Reservation", "Illuminate\\Contracts\\Queue\\ShouldQueue")),
    "routes/console.php": r"""<?php
use App\Jobs\ExpireHolds;
use Illuminate\Support\Facades\Schedule;
Schedule::job(new ExpireHolds())->everyFiveMinutes()->withoutOverlapping();
""",
    "resources/views/reservations/ticket.blade.php": """<section>
  <h1>{{ __('Your reservation') }}</h1>
  <p>{{ $reservation->count }} {{ __('admitted patrons') }}</p>
  <time>{{ $reservation->expires_at->timezone($venueTimezone ?? 'UTC') }}</time>
</section>
""",
    "database/migrations/2026_02_01_000000_add_contact_hash.php": r"""<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
return new class extends Migration {
    public function up(): void
    {
        Schema::table('reservations', fn (Blueprint $table) => $table->string('contact_hash', 64)->nullable()->index());
    }
};
""",
    "config/venue.php": "<?php\nreturn ['timezone' => env('VENUE_TIMEZONE', 'Europe/Paris'), 'floor_refresh' => 45];\n",
    "app/Services/Billing/SeatAllocator.php": _laravel_file(
        "Services\\Billing", "final class SeatAllocator { public function chargeableSeats($invoice) { return $invoice->seatCount(); } }"),
    "app/Support/Legacy/HouseRules.php": _laravel_file(
        "Support\\Legacy", "final class HouseRules {\n" +
        "".join(f"    public const HISTORIC_ROW_{n} = 'archived venue row {n}';\n" for n in range(380)) +
        "    public const EVACUATION_AISLE = 42;\n}"),
}

PYTHON = {
    "src/observatory/pipeline/decoder.py": """from observatory.protocol.crc import crc16

def decode_packet(frame: bytes) -> bytes:
    payload, checksum = frame[:-2], frame[-2:]
    if crc16(payload) != int.from_bytes(checksum, 'big'):
        raise ValueError('checksum mismatch')
    return payload
""",
    "src/observatory/protocol/crc.py": """import binascii

def crc16(payload: bytes) -> int:
    return binascii.crc_hqx(payload, 0xffff)
""",
    "src/observatory/storage/retention.py": """from datetime import timedelta

def retention_cutoff(clock, hours: int = 72):
    return clock.now() - timedelta(hours=hours)
""",
    "src/observatory/storage/sqlite.py": """from .retention import retention_cutoff

def prune(store, clock):
    return store.execute('DELETE FROM readings WHERE sampled_at < ?', (retention_cutoff(clock),))
""",
    "src/observatory/alerts/dedup.py": """def duplicate_notice(cache, station, severity):
    key = (station, severity)
    if key in cache:
        return True
    cache.add(key)
    return False
""",
    "src/observatory/alerts/routing.py": """from .dedup import duplicate_notice

def deliver(cache, notice, transport):
    if not duplicate_notice(cache, notice.station, notice.severity):
        transport.publish(notice)
""",
    "src/observatory/gateway/lease.py": """def renew_lease(clock, expires_at, owner):
    if clock.now() >= expires_at:
        raise TimeoutError('gateway lease expired')
    return owner
""",
    "src/observatory/cli/options.py": """def attach_options(parser):
    parser.add_argument('--interval', type=int, default=30)
    parser.add_argument('--station', required=True)
""",
    "src/observatory/render/options.py": """def render_options(style):
    return {'interval': 'compact', 'units': style}
""",
    "src/observatory/units/wind.py": """def wind_kph(meters_per_second):
    return round(meters_per_second * 3.6, 2)
""",
    "src/observatory/catalog/codes.py": (
        "REGION_CODES = {\n" + "".join(f"    {n!r}: 'archival station observation calibration entry',\n"
                                      for n in range(440)) + "}\n\n"
        "def aurora_region(code):\n    return REGION_CODES.get(code, 'unmapped')\n"),
}

RUST = {
    "src/protocol/frame.rs": """pub const MAX_FRAME: usize = 8192;
pub fn decode_frame(input: &[u8]) -> Option<&[u8]> {
    let announced = u16::from_be_bytes(input.get(..2)?.try_into().ok()?) as usize;
    if announced > MAX_FRAME { return None; }
    input.get(2..2 + announced)
}
""",
    "src/net/listener.rs": """use crate::protocol::frame::decode_frame;
pub fn receive(packet: &[u8]) -> Option<&[u8]> { decode_frame(packet) }
""",
    "src/queues/priority.rs": """pub fn priority_key(deadline: u64, sequence: u64) -> (u64, u64) {
    (deadline, sequence)
}
""",
    "src/worker/scheduler.rs": """use crate::queues::priority::priority_key;
pub fn order(tasks: &mut [(u64, u64)]) {
    tasks.sort_by_key(|&(deadline, sequence)| priority_key(deadline, sequence));
}
""",
    "src/security/lease.rs": """pub fn lease_valid(now: u64, expires: u64) -> bool { now < expires }
""",
    "src/cache/lease.rs": """pub fn lease_valid(age: u64, refresh_period: u64) -> bool { age < refresh_period }
""",
    "src/state/journal.rs": """use std::io::{self, Write};
pub fn append_record(writer: &mut impl Write, record: &[u8]) -> io::Result<()> {
    writer.write_all(record)?;
    writer.flush()
}
""",
    "src/config/defaults.rs": """pub const RECONNECT_MS: u64 = 250;
pub const MAX_RETRIES: u8 = 4;
""",
    "src/net/reconnect.rs": """use crate::config::defaults::{MAX_RETRIES, RECONNECT_MS};
pub fn reconnect_delay(attempt: u8) -> Option<u64> {
    (attempt < MAX_RETRIES).then(|| RECONNECT_MS << attempt)
}
""",
    "src/telemetry/metrics.rs": """pub fn gauge_key(rx: bool) -> &'static str {
    if rx { "rx_bytes" } else { "tx_bytes" }
}
""",
    "src/codec/escape.rs": (
        "pub const BYTES: &[&str] = &[\n" +
        "".join(f'    "archive codec compatibility textual calibration entry {n}",\n' for n in range(440)) +
        '];\npub fn escape_delimiter(delimiter: char) -> String { format!("\\\\{delimiter}") }\n'),
}


# Neighbouring modules provide both neutral and vocabulary-overlap distractors.
DISTRACTORS = {}
for label, entries, root, suffix, stub in [
    ("theatre", LARAVEL, "app", "php", "<?php\nreturn ['module' => '%s', 'enabled' => true];\n"),
    ("observatory", PYTHON, "src/observatory", "py", "MODULE = '%s'\nENABLED = True\n"),
    ("dispatch", RUST, "src", "rs", 'pub const MODULE: &str = "%s";\npub const ENABLED: bool = true;\n'),
]:
    distractors = DISTRACTORS[label] = set()
    for group, names in {
        "billing": "payment currency invoice balance receipt",
        "delivery": "retry priority routing delivery queue",
        "access": "lease session access identity role",
        "reports": "audit checksum retention archive region",
        "support": "defaults options timezone metrics seats",
    }.items():
        for name in names.split():
            directory = "Support" if label == "theatre" and group == "support" else group
            path = f"{root}/{directory}/{name}.{suffix}"
            entries[path] = stub % name
            distractors.add(path)


REPOSITORIES = {"theatre": LARAVEL, "observatory": PYTHON, "dispatch": RUST, **LARAVEL_PROJECTS}
for repo in LARAVEL_PROJECTS:
    DISTRACTORS[repo] = {"config/logging.php", "resources/views/dashboard.blade.php"}


def snapshot(root):
    """Hash inventory and bytes without executing or following source symlinks."""
    entries = {}
    for path in sorted(root.rglob("*")):
        metadata = path.lstat()
        if path.is_symlink() or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked confirmation source")
        if path.is_file():
            if metadata.st_nlink != 1:
                raise ValueError("Linked confirmation source")
            entries[path.relative_to(root).as_posix()] = sha256(path.read_bytes()).hexdigest()
        elif not path.is_dir():
            raise ValueError("Unexpected confirmation source type")
    return entries


def expected_inventory():
    return {f"{repo}/{path}": sha256(text.encode()).hexdigest()
            for repo, files in REPOSITORIES.items() for path, text in files.items()}


def prepare(root):
    root.mkdir(parents=True, exist_ok=False)
    for repo, files in REPOSITORIES.items():
        for name, text in files.items():
            path = root / repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.output)
    print(json.dumps({repo: len(files) for repo, files in REPOSITORIES.items()}))
