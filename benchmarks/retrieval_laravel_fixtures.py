"""Five independently authored short Laravel-style confirmation projects."""


LARAVEL_PROJECTS = {
    "archive": {
        "routes/api.php": r"""<?php
use App\Http\Controllers\DepositController;
use Illuminate\Support\Facades\Route;
Route::post('/deposits', DepositController::class)->middleware('auth:sanctum');
""",
        "app/Http/Controllers/DepositController.php": r"""<?php
namespace App\Http\Controllers;
use App\Contracts\ObjectVault;
use App\Http\Requests\DepositForm;
final class DepositController {
    public function __invoke(DepositForm $request, ObjectVault $vault) {
        return response()->json(['receipt' => $vault->ingest($request->file('bundle'))]);
    }
}
""",
        "app/Http/Requests/DepositForm.php": r"""<?php
namespace App\Http\Requests;
use Illuminate\Foundation\Http\FormRequest;
final class DepositForm extends FormRequest {
    public function rules(): array { return ['bundle' => ['required', 'file', 'mimes:tar', 'max:8192']]; }
}
""",
        "app/Contracts/ObjectVault.php": r"""<?php
namespace App\Contracts;
use Illuminate\Http\UploadedFile;
interface ObjectVault { public function ingest(UploadedFile $file): string; }
""",
        "app/Providers/ArchiveServiceProvider.php": r"""<?php
namespace App\Providers;
use App\Contracts\ObjectVault;
use App\Storage\ColdVault;
use Illuminate\Support\ServiceProvider;
final class ArchiveServiceProvider extends ServiceProvider {
    public function register(): void { $this->app->bind(ObjectVault::class, ColdVault::class); }
}
""",
        "app/Storage/ColdVault.php": r"""<?php
namespace App\Storage;
use App\Contracts\ObjectVault;
use Illuminate\Http\UploadedFile;
final class ColdVault implements ObjectVault {
    public function ingest(UploadedFile $file): string { return $file->store('acquisitions', 'cold'); }
}
""",
        "config/filesystems.php": "<?php\nreturn ['disks' => ['cold' => ['driver' => 'local', 'root' => storage_path('vault')]]];\n",
        "app/Storage/LegacyVault.php": "<?php\nnamespace App\\Storage;\nfinal class LegacyVault { public const BUNDLE_DIR = 'staging'; }\n",
    },
    "nursery": {
        "app/Models/Plant.php": r"""<?php
namespace App\Models;
use Illuminate\Database\Eloquent\Model;
final class Plant extends Model {
    public function readings() { return $this->hasMany(Moisture::class); }
}
""",
        "app/Models/Moisture.php": r"""<?php
namespace App\Models;
use Illuminate\Database\Eloquent\Model;
final class Moisture extends Model {
    protected $casts = ['sampled_at' => 'datetime', 'percentage' => 'float'];
    public function plant() { return $this->belongsTo(Plant::class); }
}
""",
        "app/Jobs/WaterDryBeds.php": r"""<?php
namespace App\Jobs;
use App\Models\Plant;
final class WaterDryBeds {
    public function handle(): void {
        Plant::whereHas('readings', fn ($r) => $r->where('percentage', '<', 18))->each(fn ($plant) => event(new \App\Events\NeedsWater($plant)));
    }
}
""",
        "routes/console.php": r"""<?php
use App\Jobs\WaterDryBeds;
use Illuminate\Support\Facades\Schedule;
Schedule::job(new WaterDryBeds())->hourly();
""",
        "app/Events/NeedsWater.php": r"""<?php
namespace App\Events;
use App\Models\Plant;
final class NeedsWater { public function __construct(public Plant $plant) {} }
""",
        "resources/views/plants/history.blade.php": "@foreach ($plant->readings as $reading)\n  {{ $reading->percentage }}%\n@endforeach\n",
        "config/nursery.php": "<?php\nreturn ['timezone' => env('GROWER_TIMEZONE'), 'dashboard_unit' => 'percent'];\n",
    },
    "tuition": {
        "app/Models/Enrollment.php": r"""<?php
namespace App\Models;
use Illuminate\Database\Eloquent\Model;
final class Enrollment extends Model {
    public function tutor() { return $this->belongsTo(User::class, 'tutor_id'); }
}
""",
        "app/Policies/EnrollmentPolicy.php": r"""<?php
namespace App\Policies;
use App\Models\{Enrollment, User};
final class EnrollmentPolicy {
    public function withdraw(User $user, Enrollment $enrollment): bool {
        return $user->id === $enrollment->tutor_id && $enrollment->starts_at->isFuture();
    }
}
""",
        "app/Http/Controllers/WithdrawalController.php": r"""<?php
namespace App\Http\Controllers;
use App\Models\Enrollment;
use Illuminate\Support\Facades\Gate;
final class WithdrawalController {
    public function __invoke(Enrollment $enrollment) {
        Gate::authorize('withdraw', $enrollment);
        $enrollment->delete();
        return response()->noContent();
    }
}
""",
        "routes/web.php": r"""<?php
use App\Http\Controllers\WithdrawalController;
use Illuminate\Support\Facades\Route;
Route::delete('/enrollments/{enrollment}', WithdrawalController::class)->middleware('auth');
""",
        "app/Notifications/LessonReminder.php": r"""<?php
namespace App\Notifications;
use Illuminate\Notifications\Notification;
final class LessonReminder extends Notification {
    public function via(object $recipient): array { return ['mail', 'database']; }
}
""",
        "resources/views/enrollments/list.blade.php": "@foreach ($enrollments as $enrollment)\n  {{ $enrollment->tutor->name }}\n@endforeach\n",
        "config/session.php": "<?php\nreturn ['lifetime' => 120, 'encrypt' => false];\n",
    },
    "freight": {
        "app/Http/Requests/ConsignmentInput.php": r"""<?php
namespace App\Http\Requests;
use Illuminate\Foundation\Http\FormRequest;
final class ConsignmentInput extends FormRequest {
    public function rules(): array { return ['pallets' => ['required', 'integer', 'between:1,44']]; }
}
""",
        "app/Services/Transit/RateCard.php": r"""<?php
namespace App\Services\Transit;
final class RateCard {
    public function surcharge(int $pallets): int { return $pallets > 40 ? 8500 : 0; }
}
""",
        "app/Services/Accounting/RateCard.php": r"""<?php
namespace App\Services\Accounting;
final class RateCard { public function tax(int $cents): int { return intdiv($cents * 15, 100); } }
""",
        "app/Http/Controllers/QuoteController.php": r"""<?php
namespace App\Http\Controllers;
use App\Http\Requests\ConsignmentInput;
use App\Services\Transit\RateCard;
final class QuoteController {
    public function __invoke(ConsignmentInput $input, RateCard $rate) {
        return ['oversize_cents' => $rate->surcharge($input->integer('pallets'))];
    }
}
""",
        "app/Models/Shipment.php": r"""<?php
namespace App\Models;
use Illuminate\Database\Eloquent\Model;
final class Shipment extends Model { protected $fillable = ['tracking_number', 'dock']; }
""",
        "routes/api.php": r"""<?php
use App\Http\Controllers\QuoteController;
use Illuminate\Support\Facades\Route;
Route::post('/quote', QuoteController::class)->middleware('throttle:quotes');
""",
        "config/freight.php": "<?php\nreturn ['loaded_by' => 'dock', 'currency' => 'USD'];\n",
    },
    "ledger": {
        "app/Models/Disbursement.php": r"""<?php
namespace App\Models;
use Illuminate\Database\Eloquent\Model;
final class Disbursement extends Model {
    protected $fillable = ['cents', 'nonce', 'member_id'];
}
""",
        "app/Actions/SubmitDisbursement.php": r"""<?php
namespace App\Actions;
use App\Models\Disbursement;
final class SubmitDisbursement {
    public function handle(array $input): Disbursement {
        return Disbursement::firstOrCreate(['nonce' => $input['nonce']], $input);
    }
}
""",
        "database/migrations/2026_03_12_000001_disbursements.php": r"""<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
return new class extends Migration {
    public function up(): void {
        Schema::create('disbursements', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('member_id');
            $table->unsignedBigInteger('cents');
            $table->string('nonce')->unique();
        });
    }
};
""",
        "app/Reports/Statement.php": r"""<?php
namespace App\Reports;
use App\Models\Disbursement;
final class Statement {
    public function netFor(int $member): int { return Disbursement::where('member_id', $member)->sum('cents'); }
}
""",
        "app/Console/Commands/DailyClose.php": r"""<?php
namespace App\Console\Commands;
use Illuminate\Console\Command;
final class DailyClose extends Command {
    protected $signature = 'ledger:close {date?}';
    public function handle(): int { return self::SUCCESS; }
}
""",
        "routes/console.php": r"""<?php
use Illuminate\Support\Facades\Schedule;
Schedule::command('ledger:close')->dailyAt('23:55');
""",
        "config/ledger.php": "<?php\nreturn ['report_currency' => 'EUR', 'report_decimals' => 2];\n",
    },
}

for files in LARAVEL_PROJECTS.values():
    files["config/logging.php"] = "<?php\nreturn ['default' => 'stack', 'deprecations' => 'null'];\n"
    files["resources/views/dashboard.blade.php"] = "<h1>{{ __('Dashboard') }}</h1>\n"
