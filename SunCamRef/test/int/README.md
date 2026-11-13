# SunCamRef system test (plan QUAL-SUNCAM, KissCam.SunCamMgr)

Harness: [fprime-testing-harness](https://github.com/LeStarch/fprime-testing-harness) v0.1.21 (`fth`).

Pin (campaign suncam-v2, DOWNLOAD priority argument): tag `v0.1.21` = tag object `d615f5ec9776f087d9dd0995522ee2a0d6ee9725` on commit
`1189871f77b84efb22e411daab19df3795acfedd`, fetched from the autobot fork
`https://github.com/lestarch-autobot/fprime-testing-harness` until it lands upstream:
`git -C harness fetch --tags https://github.com/lestarch-autobot/fprime-testing-harness && git -C harness checkout --detach v0.1.21 && pip install -e "harness[test]"`; check the pin with `git -C harness describe --tags` and `pip show fprime-testing-harness` (0.1.21).
v0.1.3 = window-slice fix (dispatchers that log `OpCodeDispatched` before the handler event); v0.1.4 = human-step, run-for-record-only tests
(`human_step` / `run_in`, verdict DEFERRED); v0.1.5 = positional `human step` procedure line → `bench.human_step()` and
`fth rfr --defer-human-steps RULING`. The deployment logs the same string at start-up (`HARNESS_DESCRIBE`, read by `fth manifest`).
v0.1.6 = `count <=|>=|<|>` n, helper metrics judged by their helper, bench `boot_event` epochs and `collect` recipe (data products into `record/raw/dp/` before every live judge), `FTH_MANIFEST` exported to the stimulus, SDD-table check insensitive to the renderer's phase marker (dry-3 / Mode B round-1 findings).
v0.1.7 = refusal fix: `boot_event` epoch rows crashed the live judge (`re.Match` indexed as a dict; SunCamRef dry-4), regression test on verbatim event.log lines.
v0.1.8 = dry-6 refusal fixes: channel epochs follow the bench `boot_event` rows, START-marker dispatch order decided by same-flush rows only, `bench.wait_any_event()` (plan `wait(A or B, N s)`) with the last-send baseline.
v0.1.9 = `wait_any_event` returns in a dry run / replay (audit parity, dry-7).
v0.1.10 = Mode B round-2 S-7/S-8: live judge settles until the channel flush passes t(END) (`timeouts.settle_s`), replay matches the plan's short command name (subtopology markers).
v0.1.11 = helper artifacts: `decode_image_in_window` writes its PNG via `ctx.artifact()` into `<run>/runner/artifacts/<test>/`; `fth render-ql` ships them beside the pages with the source `.fdp` sha256 and an index gallery in test order (L2-5's real-scene FULL first — Captain ruling); `fth package` ships `artifacts/`.
v0.1.12 = gallery ordered by decoded image size (largest = the FULL product first), then plan order; the helper's `seen` text names the PNG file only (live/replay parity).
v0.1.13 = artifact sidecar `<name>.json` (helper-declared caption, raw-mosaic min/max/mean + 256-bin histogram, optional `rgb` companion) rendered beside the image on the gallery and test page; the deployment helper writes it and a pure-Python bilinear Bayer GR→RGB demosaic (`L2-5-full-rgb.png`, no white balance) of the FULL real-scene product (Captain ruling: dark real scene stated by program; the ramp KAT previews stay grey).
v0.1.14 = harness fixes found by the dry-12 dev-campaign audit (no stimulus change): `fth audit` re-exports the record with the bench's `boot_event` exactly as `fth run` exported it; a test DEFERRED by the plugin records its `@pytest.mark.req` markers (`fth_req`) for the audit's marker comparison; `dev-campaign --ut-project` creates `ut/` before writing `ut-check.log`.
v0.1.15 = run-start markers are read as the plan's `markers.event`/`markers.arg` (`cmdDisp.NoOpStringReceived`; the auditor only knew `*.Marker` and refused RfR r1178a5f at row 5 although the markers were in the record); `fth dev-campaign` records the dry record's audit steps in `evidence.json` (`pure.audit`) and, like `fth deliver`, fails on any FAILED step or on a missing runner-vs-replay agreement.
v0.1.16 = the plan-aware marker lookup is the only form everywhere (`fth unseal` included — it had still used the legacy `*.Marker` suffix and refused RfR r2b1d714 at row 7); the manifest embeds `plan.markers`; `fth dev-campaign` runs the seed-free dev-chain gate (draw → run-start markers → unseal → package over the dry record) recorded in `evidence.json`, and `fth deliver` refuses evidence without a passing gate; `--note` records the voided runs for record.

v0.1.17 = dev-evidence html twins shipped and gated; dev-chain row 8 packages with the bundle. v0.1.18 = MARK steps align to the plan's marker command; offline quick-look re-render (`fth rerender-ql`). v0.1.19 = one procedure-step grammar (bare names are commands), PROCEDURE/RECORD MISMATCH review flags, `fth verify-stimulus` (run by `verify-plan --tests`), superseded re-renders. v0.1.20 = `verify-plan --sdd` finds the requirements table under a numbered heading (`## 2. Requirements`, SunCamMgr SDD since fprime-devices #7). v0.1.21 = package version in `pyproject.toml` matches the tag (it had stayed at 0.1.19 through v0.1.20, so `pip show` misreported the pin).

| File | Role |
| --- | --- |
| `plan.json`, `plan.md`, `faults-menu.json` | The approved plan — byte copies; any change is a plan change (anchor + reviewer). |
| `planted_faults.py` | The 5 `@planted_fault` declarations and the 4 `@helper` predicates (`version_matches_manifest`, `delta_mod`, `decode_image_in_window`, `event_count_at_most`; `memory_slot_exposure` retired with Memory Status, not implemented on the hardware); the Image data-product decoder lives here. |
| `test_<ID>.py` (19) | One stimulus per plan test, procedure transcribed verbatim; `require("STD")` for infrastructure, `check(...)` for every plan check (names are the plan's bytes), `check("ABS")` for the absence group. Metrics are judged by the plugin from `plan.json`. |
| `suncam.py`, `conftest.py` | `bracket()` (two further suncam-packet samples), `wait_any()`, `helper()` (bind a plan helper to its plan args). |
| `bench.json`, `bench/*.sh` | Bench recipe for the Raspberry Pi 5 (`flash`, `dump`, `reset`, `gds`, `recorder`, `send`); relative paths from the campaign root. |
| `../kat/` | Known-answer tests of every helper (pass + fail + unverified) on hand-built records — no bench needed. |

## Run

Host (no bench):

```sh
fth verify-plan SunCamRef/test/int/plan.json --tests SunCamRef/test/int   # plan + stimulus + fails/req consistency
python -m pytest SunCamRef/test/kat                                       # helper known-answer tests
```

Bench — campaign-root layout (`croot/`): `uut/` = this repository (submodules checked out, `cd uut/SunCamRef && fprime-util generate && fprime-util build`; after every later pull `rm -f build-fprime-*/versions/version.*` before `fprime-util build` — fprime regenerates `Svc.Version`'s describe strings only when those files are missing, and `fth manifest` rejects an image whose PROJECT version is not the current `uut` describe), `harness/` = the fth checkout, the bench recipe's `gds` line starts SunCamRef (recorded PID) together with fprime-gds and `flash` only installs (fth wants the camera UART free between flash and gds), the fth venv active, `fprime-gds`/`fprime-cli` on `PATH`.

```sh
cd croot
fth run dry-1 --manifest manifest.json --plan uut/SunCamRef/test/int/plan.json \
    --bench uut/SunCamRef/test/int/bench.json --tests uut/SunCamRef/test/int --dry-run          # full plan, dry (neutral id)
fth run dry-2 ... --dry-run --unsealed --plant L2-5=preview_instead_of_full                     # one planted fault alone
python -m pytest -p fth.pytest_plugin --fth-plan=... --fth-bench=... --fth-run-dir=... uut/SunCamRef/test/int/test_L2_5.py   # one test
fth audit --tests dry-1                                                                          # replay == live, no DIVERGENCE
```

The DpWriter directory is `<rundir>/DpCat` (`bench.json` `vars.rundir`); `dump` copies it into `record/raw/dp/`, where `decode_image_in_window` reads the Image products and writes `dev-evidence/images/<test>.png` (relative to the campaign root).

## Coverage (development evidence, harness skill §3a)

The RfR runs the pure image; the coverage *reports* are RfR inputs (`fth deliver --ut-coverage --system-coverage
--dev-evidence`). They come from `fth dev-campaign`, which needs three things this directory provides:

- **UT coverage**: a default-config UT project beside the campaign root (`utproj/settings.ini`: `framework_path`
  and `library_locations` pointing into the pinned `uut/lib/*` trees, framework/autocoder UTs off);
  `fth dev-campaign --ut-project utproj` runs `fprime-util check --coverage` there (gcovr).
- **On-target coverage**: the deployment built with `-DSUNCAMREF_COVERAGE=ON` (root `CMakeLists.txt`, separate
  build cache: `fprime-util generate --build-cache uut/build-cov -DSUNCAMREF_COVERAGE=ON && fprime-util build
  --build-cache uut/build-cov`) instruments `SunCamMgr.cpp` only (`-fprofile-filter-files`). The main plan runs
  on that image, then the one-test dump plan `test/gcov-dump/` (outside the pinned stimulus dir) on the same image: `SunCamRef.CovDump`'s
  `DUMP_COVERAGE(0, 0)` flushes the hosted libgcov counters (`__gcov_dump`; every earlier process life — the L3-1
  reset, the flash before the dump run — wrote its `.gcda` at exit, libgcov merges them) and streams the files as
  `CoverageChunk` / `CoverageObject` / `CoverageDumpDone` events, 4 chunks per 10 Hz tick, the command response
  after the last chunk. `fth coverage-system --record <dump run>/record --gcno-root uut/build-cov --project-root
  uut --filter lib/fprime-devices/fprime-devices/KissCam/Components/SunCamMgr/ --gcov gcov` places the bytes
  beside the `.gcno` (object matched by the CRC-32 of the `.gcda` path) and runs gcovr. Delete stale `*.gcda`
  under the cache before the plan run. The instrumented image is never the RfR image; in the pure image the
  component is present but `DUMP_COVERAGE` reports "no gcda root".
- **Pure run**: the plan on the RfR image (an ordinary unsealed `fth run`).

`fth dev-campaign --out dev-evidence --plan ... --tests ... --bench ... --ut-project utproj --coverage-run <plan run>
--coverage-manifest <its manifest> --dump-run <dump run> --dump-manifest <its manifest> --dump-plan test/gcov-dump/plan.json
--dump-tests test/gcov-dump --gcno-root uut/build-cov --project-root uut --filter <SunCamMgr dir> --gcov gcov --pure-run
<pure run> --pure-manifest <its manifest> --sdd <pinned sdd.md> --dictionary <dict>` exits 0 when every pure verdict is
PASS, runner == replay, and coverage meets `plan.json` `coverage` (`ut.lines_min` 95, `system.lines_min` 65; uncovered
lines must be in `not_covered_ack`).

## Windows and markers

Markers are `cmdDisp.CMD_NO_OP_STRING` / `cmdDisp.NoOpStringReceived` (`Received a NO-OP string=<id>`); the plugin sends the start/end markers of each `with window(start, end)` block; multi-window tests share the edge marker as the plan declares (L2-1, L3-1, L6-1, L6-2).
