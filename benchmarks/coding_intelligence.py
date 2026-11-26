"""Original cross-file Laravel coding controls, not workflow imitation.

Each task requires interpreting a local policy defined in a second PHP file.
The evaluator knows the repair target; unassisted arms do not get its path or
replacement line. The repair subset is deliberately restricted for safe QA.
"""
from dataclasses import dataclass

from .laravel_pilot import Case, patch_category


@dataclass(frozen=True)
class CodingFixture:
    case: Case
    companion: str
    companion_source: str
    wrong: str

    @property
    def related(self):
        return {f"app/Pilot/{self.companion}.php": self.companion_source}


def policy(name, body):
    return f"<?php\nnamespace App\\Pilot;\nfinal class {name}\n{{\n    {body}\n}}\n"


FIXTURES = (
    CodingFixture(
        Case("contact_policy", "ContactRules",
             "Fix ContactRules so email validation respects the existing ContactPolicy contract, including valid and invalid contact submissions.",
             "rules", "", "return ['required'];", "return ContactPolicy::EMAIL_RULES;",
             r"""return\s+(?:ContactPolicy::EMAIL_RULES|\[\s*['"](?:required|email|nullable|string)['"](?:\s*,\s*['"](?:required|email|nullable|string)['"]){0,3}\s*,?\s*\])\s*;""",
             r"$rules = ['address'=>ContactRules::rules()]; "
             r"$this->assertTrue(\Illuminate\Support\Facades\Validator::make(['address'=>'not-email'], $rules)->fails()); "
             r"$this->assertTrue(\Illuminate\Support\Facades\Validator::make([], $rules)->fails()); "
             r"$this->assertSame(\App\Pilot\ContactPolicy::EMAIL_RULES, ContactRules::rules());",
             r"$this->assertFalse(\Illuminate\Support\Facades\Validator::make(['address'=>'person@example.org'], ['address'=>ContactRules::rules()])->fails());"),
        "ContactPolicy",
        policy("ContactPolicy", "public const EMAIL_RULES = ['required', 'email'];"),
        "return ['required', 'string'];",
    ),
    CodingFixture(
        Case("seat_policy", "SeatEligibility",
             "Repair SeatEligibility so eligible requests follow the existing SeatPolicy limit. Do not change the policy.",
             "allows", "int $seats", "return $seats >= 1;", "return $seats >= SeatPolicy::MINIMUM;",
             r"return\s+\$seats\s*(?:>=|>|<=|<|===)\s*(?:SeatPolicy::MINIMUM|[0-9]{1,2})\s*;",
             r"$this->assertFalse(SeatEligibility::allows(\App\Pilot\SeatPolicy::MINIMUM - 1)); "
             r"$this->assertTrue(SeatEligibility::allows(\App\Pilot\SeatPolicy::MINIMUM));",
             "$this->assertTrue(SeatEligibility::allows(\App\Pilot\SeatPolicy::MINIMUM + 5));"),
        "SeatPolicy",
        policy("SeatPolicy", "public const MINIMUM = 7;"),
        "return $seats > SeatPolicy::MINIMUM;",
    ),
    CodingFixture(
        Case("editor_policy", "EditorAccess",
             "Fix EditorAccess to respect the existing EditorPolicy list and strict role matching.",
             "allows", "string $role", "return in_array($role, ['editor'], true);",
             "return in_array($role, EditorPolicy::ROLES, true);",
             r"""return\s+in_array\(\$role,\s*(?:EditorPolicy::ROLES|\[\s*['"](?:editor|reviewer|guest)['"](?:\s*,\s*['"](?:editor|reviewer|guest)['"]){0,2}\s*\]),\s*(?:true|false)\)\s*;""",
             "$this->assertTrue(EditorAccess::allows('reviewer')); "
             "$this->assertFalse(EditorAccess::allows('guest'));",
             "$this->assertTrue(EditorAccess::allows('editor')); "
             "$this->assertFalse(EditorAccess::allows('EDITOR'));"),
        "EditorPolicy",
        policy("EditorPolicy", "public const ROLES = ['editor', 'reviewer'];"),
        "return in_array($role, ['editor', 'guest'], true);",
    ),
)


def validate_fixtures():
    names = set()
    for fixture in FIXTURES:
        case = fixture.case
        if case.name in names or case.target == fixture.companion:
            raise ValueError("Duplicate fixture or invalid companion")
        names.add(case.name)
        if case.source.count(case.broken) != 1:
            raise ValueError("Ambiguous anchor")
        for replacement in (case.reference, fixture.wrong):
            if replacement == case.broken or patch_category(case, case.source.replace(case.broken, replacement)):
                raise ValueError("Invalid control")
