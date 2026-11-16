"""Opt-in, deterministic GET route-parameter fixture for disposable Laravel.

The reference fix exists only during evaluator-owned controls; hidden tests
must never be present while the real model is asked to edit its worktree.
"""
from pathlib import Path

if __package__:
    from .validation_case import fresh_fixture_path
else:
    from validation_case import fresh_fixture_path

PARAMETER_PATH = "tests/Feature/TinyBuilderParameterRegressionTest.php"
PARAMETER_HIDDEN_PATH = "tests/Feature/TinyBuilderParameterHiddenTest.php"
PARAMETER_ROUTE_URI = "tinybuilder/items/{id}"
PARAMETER_READ_TASK = (
    "Read routes/web.php and bootstrap/app.php using read_file. Explain the "
    "existing GET /tinybuilder/items/{id} endpoint. Do not edit files."
)
PARAMETER_WRITE_TASK = (
    "Read routes/web.php and tests/Feature/TinyBuilderParameterRegressionTest.php "
    "using read_file BEFORE editing. Fix GET /tinybuilder/items/{id}: accept only "
    "positive decimal integer ids, return JSON {\"id\":7} for /tinybuilder/items/7, "
    "and return HTTP 404 for non-numeric or zero ids. Preserve existing routes. "
    "Edit ONLY routes/web.php using write_file; then run "
    '["php","artisan","test"] using run_command. Do not edit tests.'
)

BAD_PARAMETER_ROUTE = """
Route::get('/tinybuilder/items/{id}', function ($id) {
    return response()->json(['id' => 0]);
});
"""

REFERENCE_PARAMETER_ROUTE = """
Route::get('/tinybuilder/items/{id}', function (string $id) {
    abort_unless(ctype_digit($id) && (int) $id > 0, 404);
    return response()->json(['id' => (int) $id]);
});
"""

VISIBLE_PARAMETER_TEST = """<?php
namespace Tests\\Feature;
use Tests\\TestCase;
class TinyBuilderParameterRegressionTest extends TestCase
{
    public function test_id_is_returned_as_an_integer(): void
    {
        $this->getJson('/tinybuilder/items/7')->assertOk()->assertExactJson(['id' => 7]);
    }
}
"""

HIDDEN_PARAMETER_TEST = """<?php
namespace Tests\\Feature;
use Tests\\TestCase;
class TinyBuilderParameterHiddenTest extends TestCase
{
    public function test_positive_id_one(): void
    {
        $this->getJson('/tinybuilder/items/1')->assertOk()->assertExactJson(['id' => 1]);
    }
    public function test_positive_id_forty_two(): void
    {
        $this->getJson('/tinybuilder/items/42')->assertOk()->assertExactJson(['id' => 42]);
    }
    public function test_non_numeric_id_returns_404(): void
    {
        $this->getJson('/tinybuilder/items/abc')->assertNotFound();
    }
    public function test_zero_id_returns_404(): void
    {
        $this->getJson('/tinybuilder/items/0')->assertNotFound();
    }
    public function test_home_route_survives(): void
    {
        $this->get('/')->assertOk();
    }
}
"""


def seed_parameter(root: Path, source: str) -> str:
    if "tinybuilder/items" in source:
        raise ValueError("Disposable baseline already has parameter benchmark route")
    target = fresh_fixture_path(root, PARAMETER_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(VISIBLE_PARAMETER_TEST, encoding="utf-8")
    return source + BAD_PARAMETER_ROUTE


def reference_fixed_parameter(source: str) -> str:
    newline = "\r\n" if "\r\n" in source else "\n"
    normalized = source.replace("\r\n", "\n")
    if normalized.count(BAD_PARAMETER_ROUTE) != 1:
        raise ValueError("Parameter seed must contain exactly one broken route")
    return normalized.replace(BAD_PARAMETER_ROUTE, REFERENCE_PARAMETER_ROUTE, 1).replace("\n", newline)


def hidden_parameter_test(slug: str | None = None, marker: str | None = None) -> str:
    if slug is None:
        return HIDDEN_PARAMETER_TEST
    if not marker:
        raise ValueError("Sibling route marker required")
    sibling = (
        "    public function test_unrelated_sibling_survives(): void\n"
        "    {\n"
        f"        $this->getJson('/{slug}')->assertOk()"
        f"->assertExactJson(['marker' => '{marker}']);\n"
        "    }\n"
    )
    return HIDDEN_PARAMETER_TEST[:-2] + sibling + "}\n"
