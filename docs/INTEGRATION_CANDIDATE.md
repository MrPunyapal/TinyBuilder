# Temporary standalone integration candidate — NOT RELEASE QUALIFIED

Base: `2a71515788b6fe4a1326776f39d926b86c2de667`.

Snapshot of exact workstream heads (original PRs and main remain unchanged):

- PR #2: `c8d035e568ac0458b4a924a99efd8492399c34a5`
- PR #3: `58b4e8f8407cb92a8cf5c2f120cd41f1d3ad4f31`
- PR #4: `c6ebceff01d231d598b132ab990ee1880aa6cb8a`
- PR #5: `c63ba92a66d10f904085354ab9e347551c63e67f`
- PR #6: `c2c8236bd4e2e31c64d442f6a00468b4d6ebbb8f`
- PR #7: `a95ac1d9d3064ac68a636160146989cffe40bce4`
- PR #8: `2271dc4acaacc35f8fb47b76ecddbbfad4d5a4d2`
- PR #9: `cbd2075c29d746cbfdbf5655e5c0b3aa97950a7b`
- PR #10: `bad313071d614cb1171f2b1212fd7a4d8dd6a53a`
- PR #11: `79184bf9c51601a8a1cb266cd29f63b8cedf9e7e`

Integration-only adjustments: preserve both changes to tests/test_parameter_harness.py; run native deterministic workflow on this integration branch with TINYBUILDER_REQUIRE_INTEGRATION=1; omit temporary application-only stale overlay workflow. No model downloads, release, or signing. This is a synthetic snapshot commit for testing, not a merge of the original PRs. Native packaging and real-model acceptance are separate gates. Windows unpublished prototype is not included.
