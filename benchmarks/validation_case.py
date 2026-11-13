"""Opt-in Laravel request-validation benchmark fixtures.

All PHP source here is *evaluator-owned*. Model tools are limited to their
disposable Laravel worktree; the reference implementation is never placed in
that worktree during inference.
"""

from pathlib import Path

VALIDATION_PATH = "tests/Feature/TinyBuilderValidationRegressionTest.php"
VALIDATION_HIDDEN_PATH = "tests/Feature/TinyBuilderValidationHiddenTest.php"
VALIDATION_ROUTE_URI = "tinybuilder/contact"

VALIDATION_READ_TASK = (
    "Read routes/web.php and bootstrap/app.php using read_file. Explain how "
    "the existing POST /tinybuilder/contact endpoint handles input. Do not edit files."
)
VALIDATION_WRITE_TASK = (
    "Read routes/web.php and tests/Feature/TinyBuilderValidationRegressionTest.php "
    "using read_file BEFORE editing. The POST /tinybuilder/contact route accepts "
    "invalid input. Require a valid email and a string message with at least "
    "3 characters; invalid JSON requests must return HTTP 422 with field errors. "
    "Valid JSON requests must return {\"accepted\":true}. Preserve every existing "
    "route. Edit ONLY routes/web.php with write_file, then run "
    '["php","artisan","test"] using run_command. Do not modify any tests.'
)

BAD_ROUTE = r"""
Route::post('/tinybuilder/contact', function (\Illuminate\Http\Request $request) {
    return response()->json(['accepted' => true]);
});
"""

REFERENCE_ROUTE = r"""
Route::post('/tinybuilder/contact', function (\Illuminate\Http\Request $request) {
    $request->validate([
        'email' => ['required', 'email'],
        'message' => ['required', 'string', 'min:3'],
    ]);
    return response()->json(['accepted' => true]);
});
"""

VISIBLE_TEST = r'''<?php
namespace Tests\Feature;
use Tests\TestCase;
class TinyBuilderValidationRegressionTest extends TestCase
{
    public function test_invalid_contact_input_is_rejected(): void
    {
        $this->postJson('/tinybuilder/contact', [
            'email' => 'invalid-email', 'message' => 'x',
        ])->assertUnprocessable()->assertJsonValidationErrors(['email', 'message']);
    }
}
'''

HIDDEN_TEST = r'''<?php
namespace Tests\Feature;
use Tests\TestCase;
class TinyBuilderValidationHiddenTest extends TestCase
{
    public function test_valid_input_returns_expected_response(): void
    {
        $this->postJson('/tinybuilder/contact', [
            'email' => 'tinybuilder@example.test', 'message' => 'A real message',
        ])->assertOk()->assertExactJson(['accepted' => true]);
    }
    public function test_missing_fields_are_rejected(): void
    {
        $this->postJson('/tinybuilder/contact', [])
            ->assertUnprocessable()->assertJsonValidationErrors(['email', 'message']);
    }
    public function test_invalid_email_is_rejected(): void
    {
        $this->postJson('/tinybuilder/contact', [
            'email' => 'not-an-email', 'message' => 'Valid message',
        ])->assertUnprocessable()->assertJsonValidationErrors(['email']);
    }
    public function test_short_message_is_rejected(): void
    {
        $this->postJson('/tinybuilder/contact', [
            'email' => 'tinybuilder@example.test', 'message' => 'ab',
        ])->assertUnprocessable()->assertJsonValidationErrors(['message']);
    }
    public function test_existing_home_route_survives(): void
    {
        $this->get('/')->assertOk();
    }
}
'''


def seed_validation(root: Path, source: str) -> str:
    """Add a broken endpoint and visible failing test in a disposable worktree."""
    if "'/tinybuilder/contact'" in source or '"/tinybuilder/contact"' in source:
        raise ValueError("Disposable baseline already has validation benchmark route")
    test = root / VALIDATION_PATH
    if test.exists():
        raise ValueError("Disposable baseline already has validation regression test")
    test.parent.mkdir(parents=True, exist_ok=True)
    test.write_text(VISIBLE_TEST, encoding="utf-8")
    return source + BAD_ROUTE


def reference_fixed_route(seeded_source: str) -> str:
    """Pure reference fix for the evaluator's separate positive-control pass."""
    if seeded_source.count(BAD_ROUTE) != 1:
        raise ValueError("Validation seed does not contain exactly one broken endpoint")
    return seeded_source.replace(BAD_ROUTE, REFERENCE_ROUTE, 1)


def hidden_validation_test(slug: str | None = None, marker: str | None = None) -> str:
    """Independent assertions; never shown to the agent while it edits."""
    if slug is None:
        return HIDDEN_TEST
    if not marker:
        raise ValueError("Sibling route marker required")
    sibling = (
        "    public function test_unrelated_sibling_route_survives(): void\n"
        "    {\n"
        f"        $this->getJson('/{slug}')->assertOk()"
        f"->assertExactJson(['marker' => '{marker}']);\n"
        "    }\n"
    )
    return HIDDEN_TEST[:-2] + sibling + "}\n"
