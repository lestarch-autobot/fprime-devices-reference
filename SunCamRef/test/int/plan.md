# QUAL-SUNCAM — KissCam.SunCamMgr on SunCamRef (fprime-devices-reference, Raspberry Pi 5 aarch64)

## 0 Scope
- UUT: `KissCam.SunCamMgr` (fprime-community/fprime-devices, `fprime-devices/KissCam`), SHA recorded in the manifest at stage 2.
- Deployment: `SunCamRef` in fprime-community/fprime-devices-reference (human-directed test deployment; the repository was empty): CdhCore + ComFprime (TCP to the GDS on the Pi) + DataProducts + FileHandling subtopologies, Svc.Version, Svc.PrmDb, rate groups 1/10 Hz, `uartDriver: Drv.PosixUartDriver` on /dev/ttyUSB0 115200 8N1, `sunCamMgr: KissCam.SunCamMgr` driven by the 10 Hz rate group.
- Bench: Raspberry Pi 5 `devin` (aarch64, Debian), KissCAM V2 bench unit powered on, FTDI USB-RS422 cable FTAQMGVF → /dev/ttyUSB0; foreign /dev/ttyACM1-3 never touched; no software power control (the camera's USB power port cannot be switched; human power cycle in L8-1 only).
- Camera counters (RXV, RXF, uptime) persist across FSW restarts and runs — never asserted absolutely, only as deltas (mod 256) or ignored.
- Ground system: fprime-gds (harness skill default); recorder fprime-cli events/channels.
- Order: L0-1, L0-2, L2-1 … L2-10, L2-11, L3-1, L5-1, L5-3, L6-1, L6-2, L7-1, L8-1; every `setup` names the state the previous test leaves.
- L8-1 is the one human-in-the-loop test (`run_in: ["rfr"]`, `human_step`): deferred in dry runs and rehearsal, executed only in the run-for-record with the human step prompted by the runner.
- Out of scope: WRITE_REGISTER (excluded by the request), camera power sequencing, HD FULL download on the bench (1920 lines, 4 × L2-5), datasheet features the unit does not implement (Memory Status, 80×60 preview, camera-side parameter errors — SDD §Hardware notes), downlink of products (DpCatalog/FileDownlink are deployment services).

## 1 Entry gates
- Stage-1 close: `fprime-util check` on `KissCam/Components/SunCamMgr` passes with every row of the SDD unit-test list implemented.
- Image: `SunCamRef` built for aarch64 from the manifest SHAs (fprime-devices, fprime, fprime-devices-reference, harness) with Svc.Version strings; installed on the Pi by the bench `flash` script; dictionary from that build.
- Marker round-trip: `cmdDisp.CMD_NO_OP_STRING` → `NoOpStringReceived` (format `Received a NO-OP string={}`, CmdDispatcher.fpp) byte-exact in the record (L0-2); event budget ≤ 60 events per test window.
- Bench recipe: `bench.json` (flash = install + restart SunCamRef by recorded PID; dump = copy of the running binary + copy of the DpWriter output directory into record/raw/dp/; reset = restart by recorded PID, settle ≥ 3 s; gds/recorder/send via fprime-gds + fprime-cli on the Pi); `/dev/ttyUSB0` held by no other process.
- Camera precondition: powered on, idle; L2-1 SETUP_CAMERA establishes READY — no test assumes a prior camera state except as its `setup` says.
- §7 refresh at stage 2 confirms on the bench: event text/enum rendering against the SunCamRef dictionary; slot memory intact across a mode change (L2-9); HD capture duration and the 192-line HD preview product (L2-10); HD download reply mode byte 03 → header imageMode HD; all four slots re-captured in SD after the HD capture (L2-10); download durations (L2-4/L2-5).

## 2 Test levels
L0 provenance/feasibility · L2 functional · L3 persistence/reset · L5 fault paths · L6 negative controls · L7 final state for independent verification · L8 human-in-the-loop (run-for-record only).

## 3 Test entries

Window rule: rows from the **last** `cmdDisp.NoOpStringReceived(id=START)` row that precedes the first `cmdDisp.NoOpStringReceived(id=END)` row following it, through that END row plus the END `cmdDisp.CMD_NO_OP_STRING` command's own `cmdDisp` rows (at most two), inclusive; ordering key `t = epoch·1e6 + fsw`, archive index on ties. Channel rows are those with `t` between the first and last window event. `commands_sent` = commands from the matching START sending (its last sending if re-sent) through the END sending, inclusive.

Standard `complete` block (STD): both markers present; commands_sent == count(event cmdDisp.OpCodeDispatched); event cmdDisp.TooManyCommands count == 0; suncam samples >= 2.
Standard absence block (ABS): event sunCamMgr.QueueOverflow count == 0; event sunCamMgr.SendFailed count == 0; event sunCamMgr.ProductAllocationFailed count == 0; event sunCamMgr.ModeMismatch count == 0; event sunCamMgr.ReplyTimeout count == 0; event sunCamMgr.FrameDiscarded count == 0; event sunCamMgr.DownloadFailed count == 0.
Packets (named channel sets for `<packet> samples >= n`): suncam = sunCamMgr.SetupState, sunCamMgr.CurrentOperation, sunCamMgr.Exchanges, sunCamMgr.CameraErrors, sunCamMgr.Timeouts, sunCamMgr.DiscardedBytes, sunCamMgr.MalformedReplies, sunCamMgr.ImagesCaptured, sunCamMgr.LinesDownloaded, sunCamMgr.ProductsSent, sunCamMgr.QueueOverflows; Health = rateGroup1.RgCycleSlips.

ID:        L0-1
Title:     Image identity and boot state
Purpose:   Image identity and boot state
Covers:    REQ-SunCamMgr-002, REQ-SunCamMgr-030 — REQ-002 (no camera exchange at boot); REQ-030 (quiet window: ≥ 2 suncam samples prove the periodic write); image_version policy required
Setup:     SunCamRef installed by the bench flash script, GDS attached, ≥ 3 s after start; no SunCamMgr command sent since boot (only the run-start markers).
Procedure: MARK(10); bracket (2 suncam samples); version.VERSION(ALL); bracket (2 suncam samples); MARK(11).
Window:    Marker(id=10) … Marker(id=11)
Pass rule: named checks declared in the integration test (test_L0_1).
Evidence:  Version payloads equal the manifest describe strings; SetupState NOT_SETUP, Exchanges 0 at boot.
Planted faults:none

ID:        L0-2
Title:     Marker round-trip
Purpose:   Marker round-trip
Covers:    REQ-SunCamMgr-030 — entry gate (harness completeness); REQ-030 via the quiet-window samples
Setup:     As L0-1.
Procedure: MARK(20); bracket (2 suncam samples); MARK(4294901759); bracket (2 suncam samples); MARK(21).
Window:    Marker(id=20) … Marker(id=21)
Pass rule: named checks declared in the integration test (test_L0_2).
Evidence:  Three NoOpStringReceived events in order, the probe id one below reserved_min.
Planted faults:none

ID:        L2-1
Title:     Set-up from NOT_SETUP and re-entrant from READY
Purpose:   Set-up from NOT_SETUP and re-entrant from READY
Covers:    REQ-SunCamMgr-001, REQ-SunCamMgr-003, REQ-SunCamMgr-005, REQ-SunCamMgr-012, REQ-SunCamMgr-022, REQ-SunCamMgr-023
Setup:     Camera on; component NOT_SETUP (fresh boot); parameters at defaults (CAMERA_MODE SD, EXPOSURE 672).
Procedure: MARK(210); bracket (2 suncam samples); sunCamMgr.SETUP_CAMERA; wait(SetupComplete, 15 s); bracket (2 suncam samples); MARK(212); bracket (2 suncam samples); sunCamMgr.EXPOSURE_PRM_SET(300); wait(ExposureReadback, 5 s); sunCamMgr.SETUP_CAMERA; wait(SetupComplete, 15 s); sunCamMgr.EXPOSURE_PRM_SET(672); wait(ExposureReadback, 5 s); bracket (2 suncam samples); MARK(211).
Window:    W1 = Marker(id=210) … Marker(id=212); W2 = Marker(id=212) … Marker(id=211)
Pass rule: named checks declared in the integration test (test_L2_1). metrics: W1: t(event sunCamMgr.SetupComplete(mode=SD, exposure=672)) - t(sunCamMgr.SETUP_CAMERA sent) <= 12 s (5 exchanges × 2 s timeout bound (REPLY_TIMEOUT_TICKS 20 at 10 Hz); nominal < 1 s).
Evidence:  W1: SetupComplete 672 from NOT_SETUP. W2: push 300 then re-entrant SETUP_CAMERA reports exposure 300 (non-default, so the Set Exposure frame is proven); defaults restored.
Planted faults:expect_wrong_exposure_resetup

ID:        L2-2
Title:     Ping MCU and MCU+sensor
Purpose:   Ping MCU and MCU+sensor
Covers:    REQ-SunCamMgr-006, REQ-SunCamMgr-022, REQ-SunCamMgr-025
Setup:     READY (after L2-1).
Procedure: MARK(220); bracket (2 suncam samples); sunCamMgr.PING(MCU); wait(PingReply, 5 s); sunCamMgr.PING(MCU_AND_SENSOR); wait(PingReply, 5 s); bracket (2 suncam samples); MARK(221).
Window:    Marker(id=220) … Marker(id=221)
Pass rule: named checks declared in the integration test (test_L2_2).
Evidence:  Two PingReply events with the camera's counters; RXV +1, RXF +0.
Planted faults:none

ID:        L2-3
Title:     Capture test pattern and live frame
Purpose:   Capture test pattern and live frame
Covers:    REQ-SunCamMgr-001, REQ-SunCamMgr-013, REQ-SunCamMgr-022, REQ-SunCamMgr-025, REQ-SunCamMgr-033
Setup:     READY, mode SD, exposure 672.
Procedure: MARK(230); bracket (2 suncam samples); sunCamMgr.CAPTURE(SLOT_3, ON); wait(CaptureComplete, 10 s); sunCamMgr.CAPTURE(SLOT_0, OFF); wait(CaptureComplete, 10 s); bracket (2 suncam samples); MARK(231).
Window:    Marker(id=230) … Marker(id=231)
Pass rule: named checks declared in the integration test (test_L2_3).
Evidence:  Two CaptureComplete events (0-byte ACKs, §7.4.5 response figure: the exposure argument is the Exposure channel value, 672); ImagesCaptured +2.
Planted faults:none

ID:        L2-4
Title:     Preview download → Image data product (decoded)
Purpose:   Preview download → Image data product (decoded)
Covers:    REQ-SunCamMgr-001, REQ-SunCamMgr-014, REQ-SunCamMgr-015, REQ-SunCamMgr-037
Setup:     READY; slot 3 holds the test pattern (L2-3).
Procedure: MARK(240); bracket (2 suncam samples); sunCamMgr.DOWNLOAD(SLOT_3, PREVIEW, 0); wait(DownloadComplete, 20 s); bracket (2 suncam samples); MARK(241).
Window:    Marker(id=240) … Marker(id=241)
Pass rule: named checks declared in the integration test (test_L2_4). metrics: t(event sunCamMgr.DownloadComplete(slot=SLOT_3, imageMode=SD, resolution=PREVIEW, lines=48, bytes=3072)) - t(sunCamMgr.DOWNLOAD sent) <= 10 s (48 replies × 72 B (6 framing + 2 line-number + 64 pixels; SDD §Hardware notes, Preview image) at 11 520 B/s ≈ 0.3 s + camera latency; 10 s bound).
Evidence:  48 lines, no Memory Status (SDD §Hardware notes, Memory Status): DownloadComplete lines=48 bytes=3072; the product file in the record decodes to dev-evidence/images/L2-4-preview.png (the request's decoded data-product image).
Planted faults:none

ID:        L2-5
Title:     Full download → Image data product (decoded)
Purpose:   Full download → Image data product (decoded)
Covers:    REQ-SunCamMgr-014
Setup:     READY; slot 0 holds a live SD frame (L2-3).
Procedure: MARK(250); bracket (2 suncam samples); sunCamMgr.DOWNLOAD(SLOT_0, FULL, 0); wait(DownloadComplete, 120 s); bracket (2 suncam samples); MARK(251).
Window:    Marker(id=250) … Marker(id=251)
Pass rule: named checks declared in the integration test (test_L2_5). metrics: t(event sunCamMgr.DownloadComplete(slot=SLOT_0, imageMode=SD, resolution=FULL, lines=480, bytes=307200)) - t(sunCamMgr.DOWNLOAD sent) <= 90 s (480 × 648 B (6 + 2 + 640, §7.4.6) at 11 520 B/s ≈ 27 s + latency; 3× margin); event sunCamMgr.LineRetry count <= 4 (≤ 1 % line retries guards the receive-pool/queue sizing of the topology SDD).
Evidence:  DownloadComplete lines=480 bytes=307200; decoded Bayer PNG in dev-evidence/images/L2-5-full.png.
Planted faults:preview_instead_of_full

ID:        L2-6
Title:     EXPOSURE parameter push and readback
Purpose:   EXPOSURE parameter push and readback
Covers:    REQ-SunCamMgr-010, REQ-SunCamMgr-012, REQ-SunCamMgr-023
Setup:     READY, idle, exposure 672.
Procedure: MARK(260); bracket (2 suncam samples); sunCamMgr.EXPOSURE_PRM_SET(300); wait(ExposureReadback, 5 s); sunCamMgr.EXPOSURE_PRM_SET(672); wait(ExposureReadback, 5 s); bracket (2 suncam samples); MARK(261).
Window:    Marker(id=260) … Marker(id=261)
Pass rule: named checks declared in the integration test (test_L2_6).
Evidence:  Two SettingApplied/ExposureReadback pairs; Exposure channel follows the push.
Planted faults:expect_wrong_exposure_push

ID:        L2-7
Title:     Sleep from READY and from NOT_SETUP; READY-only command rejected
Purpose:   Sleep from READY and from NOT_SETUP; READY-only command rejected
Covers:    REQ-SunCamMgr-006, REQ-SunCamMgr-007, REQ-SunCamMgr-008
Setup:     READY.
Procedure: MARK(270); bracket (2 suncam samples); sunCamMgr.SLEEP; wait(SleepEntered, 5 s); sunCamMgr.SLEEP; wait(SleepEntered, 5 s); sunCamMgr.CAPTURE(SLOT_0, OFF); wait(CommandRejected, 5 s); sunCamMgr.PING(MCU); wait(PingReply, 5 s); bracket (2 suncam samples); MARK(271).
Window:    Marker(id=270) … Marker(id=271)
Pass rule: named checks declared in the integration test (test_L2_7).
Evidence:  SleepEntered twice (second from NOT_SETUP); CAPTURE rejected NOT_READY without a frame; PING accepted while NOT_SETUP.
Planted faults:none

ID:        L2-8
Title:     Register read of the exposure register
Purpose:   Register read of the exposure register
Covers:    REQ-SunCamMgr-012, REQ-SunCamMgr-025
Setup:     NOT_SETUP (after L2-7); the test re-establishes READY.
Procedure: MARK(280); bracket (2 suncam samples); sunCamMgr.SETUP_CAMERA; wait(SetupComplete, 15 s); sunCamMgr.EXPOSURE_PRM_SET(300); wait(ExposureReadback, 5 s); sunCamMgr.READ_REGISTER(12306); wait(RegisterRead or CameraError, 5 s); sunCamMgr.EXPOSURE_PRM_SET(672); wait(ExposureReadback, 5 s); bracket (2 suncam samples); MARK(281).
Window:    Marker(id=280) … Marker(id=281)
Pass rule: named checks declared in the integration test (test_L2_8).
Evidence:  RegisterRead 0x3012 = 300 after a non-default push; defaults restored.
Planted faults:read_wrong_register

ID:        L2-9
Title:     CAMERA_MODE push re-pushes exposure
Purpose:   CAMERA_MODE push re-pushes exposure
Covers:    REQ-SunCamMgr-010, REQ-SunCamMgr-012, REQ-SunCamMgr-023, REQ-SunCamMgr-027
Setup:     READY, SD, exposure 672 (after L2-8).
Procedure: MARK(290); bracket (2 suncam samples); sunCamMgr.EXPOSURE_PRM_SET(300); wait(ExposureReadback, 5 s); sunCamMgr.CAMERA_MODE_PRM_SET(HD); wait(ExposureReadback, 5 s); sunCamMgr.CAMERA_MODE_PRM_SET(SD); wait(ExposureReadback, 5 s); sunCamMgr.EXPOSURE_PRM_SET(672); wait(ExposureReadback, 5 s); bracket (2 suncam samples); MARK(291).
Window:    Marker(id=290) … Marker(id=291)
Pass rule: named checks declared in the integration test (test_L2_9).
Evidence:  Each mode push is followed by an exposure push and readback at the non-default 300; mode HD then SD; no capture, slot contents untouched.
Planted faults:none

ID:        L2-10
Title:     HD capture and preview download → four-quadrant 128×96 product tagged HD
Purpose:   HD capture and preview download → four-quadrant 128×96 product tagged HD
Covers:    REQ-SunCamMgr-013, REQ-SunCamMgr-014, REQ-SunCamMgr-015, REQ-SunCamMgr-033
Setup:     READY, SD, exposure 672 (after L2-9). An HD capture writes all four slots, so SD live frames are re-captured into slots 0..3 afterwards (slot 3 pattern re-captured by L7-1).
Procedure: MARK(2100); bracket (2 suncam samples); sunCamMgr.CAMERA_MODE_PRM_SET(HD); wait(ExposureReadback, 5 s); sunCamMgr.CAPTURE(SLOT_0, ON); wait(CaptureComplete, 20 s); sunCamMgr.DOWNLOAD(SLOT_0, PREVIEW, 0); wait(DownloadComplete, 60 s); sunCamMgr.CAMERA_MODE_PRM_SET(SD); wait(ExposureReadback, 5 s); sunCamMgr.CAPTURE(SLOT_0, OFF); wait(CaptureComplete, 10 s); sunCamMgr.CAPTURE(SLOT_1, OFF); wait(CaptureComplete, 10 s); sunCamMgr.CAPTURE(SLOT_2, OFF); wait(CaptureComplete, 10 s); sunCamMgr.CAPTURE(SLOT_3, OFF); wait(CaptureComplete, 10 s); bracket (2 suncam samples); MARK(2101).
Window:    Marker(id=2100) … Marker(id=2101)
Pass rule: named checks declared in the integration test (test_L2_10). metrics: t(event sunCamMgr.DownloadComplete(slot=SLOT_0, imageMode=HD, resolution=PREVIEW, lines=192, bytes=12288)) - t(sunCamMgr.DOWNLOAD sent) <= 40 s (193 exchanges × 72 B ≈ 1.2 s at 11 520 B/s + camera latency (≈ 4 × the L2-4 preview); HD FULL (1920 lines ≈ 4 × L2-5) is not run on the bench).
Evidence:  One four-quadrant product tagged HD from DOWNLOAD(SLOT_0, PREVIEW, 0) after an HD test-pattern capture; decoded 128×96 PNG with the quadrants placed by slot tag; camera back in SD with live frames re-captured in all four slots.
Planted faults:none

ID:        L2-11
Title:     Preview download with commanded priority → Image product priority 7
Purpose:   Preview download with commanded priority → Image product priority 7
Covers:    REQ-SunCamMgr-037
Setup:     READY, SD, exposure 672; slot 3 holds a live SD frame (re-captured in L2-10).
Procedure: MARK(2110); bracket (2 suncam samples); sunCamMgr.DOWNLOAD(SLOT_3, PREVIEW, 7); wait(DownloadComplete, 20 s); bracket (2 suncam samples); MARK(2111).
Window:    Marker(id=2110) … Marker(id=2111)
Pass rule: named checks declared in the integration test (test_L2_11). metrics: t(event sunCamMgr.DownloadComplete(slot=SLOT_3, imageMode=SD, resolution=PREVIEW, lines=48, bytes=3072)) - t(sunCamMgr.DOWNLOAD sent) <= 10 s (as L2-4 (48 × 72 B at 11 520 B/s ≈ 0.3 s + camera latency)).
Evidence:  One Image product whose header priority is 7 from DOWNLOAD(SLOT_3, PREVIEW, 7); decoded 64×48 PNG.
Planted faults:none

ID:        L3-1
Title:     EXPOSURE persists across a restart
Purpose:   EXPOSURE persists across a restart
Covers:    REQ-SunCamMgr-003, REQ-SunCamMgr-005, REQ-SunCamMgr-010, REQ-SunCamMgr-027
Setup:     READY.
Procedure: MARK(310); bracket (2 suncam samples); sunCamMgr.EXPOSURE_PRM_SET(400); wait(ExposureReadback, 5 s); sunCamMgr.EXPOSURE_PRM_SAVE; prmDb.PRM_SAVE_FILE; wait(prmDb.PrmFileSaveComplete, 10 s); bracket (2 suncam samples); MARK(311); action: bench reset (restart SunCamRef by recorded PID; ≥ 3 s settle); bracket (2 suncam samples); MARK(312); bracket (2 suncam samples); sunCamMgr.SETUP_CAMERA; wait(SetupComplete, 15 s); sunCamMgr.EXPOSURE_PRM_SET(672); wait(ExposureReadback, 5 s); sunCamMgr.EXPOSURE_PRM_SAVE; prmDb.PRM_SAVE_FILE; wait(prmDb.PrmFileSaveComplete, 10 s); bracket (2 suncam samples); MARK(313).
Window:    W1 = Marker(id=310) … Marker(id=311); R = Marker(id=311) … Marker(id=312) (reset window); W2 = Marker(id=312) … Marker(id=313)
Pass rule: named checks declared in the integration test (test_L3_1).
Evidence:  After the restart SETUP_CAMERA applies the saved 400; defaults restored and saved at the end.
Planted faults:none

ID:        L5-1
Title:     Busy rejection and commanded download abort
Purpose:   Busy rejection and commanded download abort
Covers:    REQ-SunCamMgr-009, REQ-SunCamMgr-017
Setup:     READY; slot 0 holds a frame.
Procedure: MARK(510); bracket (2 suncam samples); sunCamMgr.DOWNLOAD(SLOT_0, FULL, 0); wait(DownloadStarted, 5 s); sunCamMgr.PING(MCU); wait(CommandRejected, 5 s); sunCamMgr.DOWNLOAD_ABORT; wait(DownloadAborted, 10 s); bracket (2 suncam samples); MARK(511).
Window:    Marker(id=510) … Marker(id=511)
Pass rule: named checks declared in the integration test (test_L5_1).
Evidence:  CommandRejected BUSY then DownloadAborted (ACTIVITY_HI, commanded); the partial product is sent; no DownloadFailed.
Planted faults:none

ID:        L5-3
Title:     Out-of-range exposure refused locally; set-up fails before Set Exposure
Purpose:   Out-of-range exposure refused locally; set-up fails before Set Exposure
Covers:    REQ-SunCamMgr-002, REQ-SunCamMgr-004, REQ-SunCamMgr-031
Setup:     READY, exposure 672.
Procedure: MARK(530); bracket (2 suncam samples); sunCamMgr.EXPOSURE_PRM_SET(1); wait(SettingRejected, 5 s); sunCamMgr.SETUP_CAMERA; wait(SetupFailed, 15 s); sunCamMgr.EXPOSURE_PRM_SET(672); wait(2 s); sunCamMgr.SETUP_CAMERA; wait(SetupComplete, 15 s); bracket (2 suncam samples); MARK(531).
Window:    Marker(id=530) … Marker(id=531)
Pass rule: named checks declared in the integration test (test_L5_3).
Evidence:  EXPOSURE 1 is refused without a frame (READY kept, Exposure channel unchanged); SETUP_CAMERA with the persisted 1 stops at SET_EXPOSURE after Ping MCU and Set Mode (NOT_SETUP, WARNING_HI); 672 restored, set-up completes.
Planted faults:none

ID:        L6-1
Title:     Negative control: READY-only commands refused while NOT_SETUP
Purpose:   Negative control: READY-only commands refused while NOT_SETUP
Covers:    REQ-SunCamMgr-002, REQ-SunCamMgr-007, REQ-SunCamMgr-008, REQ-SunCamMgr-026, REQ-SunCamMgr-036
Setup:     READY (after L5-3); W1 puts the component in NOT_SETUP.
Procedure: MARK(610); bracket (2 suncam samples); sunCamMgr.SLEEP; wait(SleepEntered, 5 s); bracket (2 suncam samples); MARK(612); bracket (2 suncam samples); sunCamMgr.PING(MCU); wait(PingReply, 5 s); sunCamMgr.CAPTURE(SLOT_0, OFF); sunCamMgr.DOWNLOAD(SLOT_0, PREVIEW, 0); sunCamMgr.READ_REGISTER(12306); sunCamMgr.DOWNLOAD_ABORT; wait(2 s); sunCamMgr.PING(MCU); wait(PingReply, 5 s); bracket (2 suncam samples); MARK(611).
Window:    W1 = Marker(id=610) … Marker(id=612); W = Marker(id=612) … Marker(id=611)
Pass rule: named checks declared in the integration test (test_L6_1).
Evidence:  Four CommandRejected events; Exchanges +2 (the two pings) and the camera's own RXV +1 — outside-UUT evidence that no refused command was sent.
Planted faults:none

ID:        L6-2
Title:     Negative control: DOWNLOAD_ABORT with no download
Purpose:   Negative control: DOWNLOAD_ABORT with no download
Covers:    REQ-SunCamMgr-026
Setup:     NOT_SETUP (after L6-1); W1 re-establishes READY.
Procedure: MARK(620); bracket (2 suncam samples); sunCamMgr.SETUP_CAMERA; wait(SetupComplete, 15 s); bracket (2 suncam samples); MARK(622); bracket (2 suncam samples); sunCamMgr.PING(MCU); wait(PingReply, 5 s); sunCamMgr.DOWNLOAD_ABORT; wait(CommandRejected, 5 s); sunCamMgr.PING(MCU); wait(PingReply, 5 s); bracket (2 suncam samples); MARK(621).
Window:    W1 = Marker(id=620) … Marker(id=622); W = Marker(id=622) … Marker(id=621)
Pass rule: named checks declared in the integration test (test_L6_2).
Evidence:  One CommandRejected NO_DOWNLOAD while READY and idle; Exchanges +2 and RXV +1 (the two pings): no frame for the refused command.
Planted faults:none

ID:        L7-1
Title:     Final state: test-pattern capture, preview product on disk
Purpose:   Final state: test-pattern capture, preview product on disk
Covers:    REQ-SunCamMgr-001, REQ-SunCamMgr-013, REQ-SunCamMgr-015
Setup:     READY (after L6-2).
Procedure: MARK(710); bracket (2 suncam samples); sunCamMgr.CAPTURE(SLOT_3, ON); wait(CaptureComplete, 10 s); sunCamMgr.DOWNLOAD(SLOT_3, PREVIEW, 0); wait(DownloadComplete, 20 s); bracket (2 suncam samples); MARK(711).
Window:    Marker(id=710) … Marker(id=711)
Pass rule: named checks declared in the integration test (test_L7_1).
Evidence:  The product written during this window (not any earlier one) decodes to the test pattern; slot 3 is left holding the pattern for the independent read.
Planted faults:sleep_before_final

ID:        L8-1
Title:     Camera power-on (human step; run-for-record only, DEFERRED in rehearsal and dry runs) → set-up
Purpose:   Camera power-on (human step; run-for-record only, DEFERRED in rehearsal and dry runs) → set-up
Covers:    REQ-SunCamMgr-003, REQ-SunCamMgr-020, REQ-SunCamMgr-034, REQ-SunCamMgr-036
Setup:     READY (after L7-1); W1 puts the component in NOT_SETUP with the camera still on; the human step then power-cycles the camera.
Procedure: MARK(810); bracket (2 suncam samples); sunCamMgr.SLEEP; wait(SleepEntered, 5 s); bracket (2 suncam samples); MARK(812); human step (runner prompt: human_step); wait(3 s); sunCamMgr.SETUP_CAMERA; wait(SetupComplete, 15 s); bracket (2 suncam samples); MARK(811).
Window:    W1 = Marker(id=810) … Marker(id=812); W = Marker(id=812) … Marker(id=811)
Pass rule: named checks declared in the integration test (test_L8_1).
Evidence:  Human-in-the-loop: one power-on line discarded while NOT_SETUP, no CameraRestarted, then a complete set-up to READY; executed in the run-for-record only (the runner prompts the human step).
Planted faults:none
Human step:The component is NOT_SETUP. Confirm the camera is OFF (unplug its USB power if it is on, wait 5 s); power it ON; type CONFIRM when its LED/power is on.
Run in:    rfr (human step; run-for-record only)

## 4 Traceability
| REQ | Tests | Note |
|---|---|---|
| REQ-SunCamMgr-001 | L2-1, L2-3, L2-4, L7-1 |  |
| REQ-SunCamMgr-002 | L0-1, L5-3, L6-1 | negative control: no frame before SETUP_CAMERA — UUT Exchanges and the camera's own RXV (L6-1) |
| REQ-SunCamMgr-003 | L2-1, L3-1 + L8-1 (run-for-record only: set-up after a camera power cycle) |  |
| REQ-SunCamMgr-004 | L5-3 (single bench test, never planted) + UT | local set-up failure (out-of-range EXPOSURE at SET_EXPOSURE) on the bench; camera-side step failures in UT |
| REQ-SunCamMgr-005 | L2-1, L3-1 | L2-1 W2 re-runs SETUP_CAMERA while READY |
| REQ-SunCamMgr-006 | L2-2, L2-7 |  |
| REQ-SunCamMgr-007 | L2-7, L6-1 |  |
| REQ-SunCamMgr-008 | L2-7, L6-1 |  |
| REQ-SunCamMgr-009 | L5-1 (single bench test, never planted) + UT | a second bench BUSY test would repeat L5-1; the plan keeps L5-1 fault-free so the draw never leaves REQ-009 uncovered |
| REQ-SunCamMgr-010 | L2-6, L2-9, L3-1 |  |
| REQ-SunCamMgr-011 | waived: Unit Test | a camera-refused push needs a camera fault (the component now range-checks EXPOSURE, so Set Exposure 1 is never sent): timeout/0xFF/send-failed pushes are unit tests |
| REQ-SunCamMgr-012 | L2-1, L2-6, L2-8, L2-9 |  |
| REQ-SunCamMgr-013 | L2-3, L2-10, L7-1 |  |
| REQ-SunCamMgr-014 | L2-4, L2-5, L2-10 |  |
| REQ-SunCamMgr-015 | L2-4, L2-10, L7-1 | product decoded by the helper from the record (header + lines) |
| REQ-SunCamMgr-016 | waived: Unit Test | line failure needs a camera fault mid-download: not plantable on this bench |
| REQ-SunCamMgr-017 | L5-1 (single bench test, never planted) + UT | commanded abort on the bench; LINE_FAILED/SEND_FAILED/PRODUCT_FULL aborts in UT |
| REQ-SunCamMgr-018 | waived: Unit Test | reply timeout needs a silent camera: no power control |
| REQ-SunCamMgr-019 | waived: Unit Test | no documented command yields an error frame on this unit (SDD §Hardware notes, Camera-side parameter validation), so no bench stimulus; 0xFF replies are unit-tested (testCameraErrorReply) |
| REQ-SunCamMgr-020 | L8-1 (run-for-record only) + UT | the power-on line while NOT_SETUP is exercised by L8-1 (human power cycle, run-for-record only); stray/malformed bytes need a second writer on the bus — testMalformedAndStrayFrames, testPowerOnBanner |
| REQ-SunCamMgr-021 | waived: Unit Test | mode mismatch while READY needs a camera power-cycle |
| REQ-SunCamMgr-022 | L2-1, L2-2, L2-3 |  |
| REQ-SunCamMgr-023 | L2-1, L2-6, L2-9 |  |
| REQ-SunCamMgr-024 | waived: Unit Test | UART send failure / product allocation failure are not plantable without breaking the deployment |
| REQ-SunCamMgr-025 | L2-2, L2-3, L2-8 |  |
| REQ-SunCamMgr-026 | L6-1, L6-2 |  |
| REQ-SunCamMgr-027 | L2-9, L3-1 |  |
| REQ-SunCamMgr-028 | waived: Unit Test | exposure readback mismatch needs a camera that answers a different value: UT only |
| REQ-SunCamMgr-029 | waived: Unit Test | queue-full hooks are unreachable at 10 Hz / 115200 baud without a flood tool |
| REQ-SunCamMgr-030 | L0-1, L0-2 (period: UT) | exact tick period is a unit test; ≥ 2 samples of every suncam channel in a quiet window (L0-1, L0-2: nothing changes) is the bench proof of the periodic write |
| REQ-SunCamMgr-031 | L5-3 (single bench test, never planted) + UT | refused push and refused set-up step on the bench; boundary values 2/960/961 in UT |
| REQ-SunCamMgr-033 | L2-3, L2-10 | 0-byte Capture ACK (Datasheet Rev 1.3 §7.4.5 response figure): CaptureComplete.exposure = the Exposure channel value, 672 (L2-3 live capture, L2-10 four SD re-captures) |
| REQ-SunCamMgr-034 | L8-1 (run-for-record only, tolerance side) + UT (detection side) | detection side (READY) unit test; tolerance side L8-1 (run-for-record only) — the camera's USB power cannot be switched by software (uhubctl sweep found nothing), so the human powers the camera on at the runner's prompt |
| REQ-SunCamMgr-035 | waived: Unit Test | HD slot rule (SLOT_0 only; CommandRejected HD_SLOT otherwise) — testDownloadHdFourSlots; L2-10 exercises the accepted SLOT_0 path only |
| REQ-SunCamMgr-036 | L6-1, L8-1 | CAPTURE refused NOT_READY while NOT_SETUP (L6-1: no frame reaches the camera, RXV unchanged); L8-1: NOT_SETUP across the camera power cycle, Capture only after set-up — testNoCaptureWhenNotSetup |
| REQ-SunCamMgr-037 | L2-4, L2-11 | container priority decoded from the product file: 0 → IMAGE_DP_PRIORITY (10) in L2-4, 7 in L2-11 |

## 5 Metrics
- L2-1: t(event sunCamMgr.SetupComplete(mode=SD, exposure=672)) - t(sunCamMgr.SETUP_CAMERA sent) <= 12 s
- L2-4: t(event sunCamMgr.DownloadComplete(slot=SLOT_3, imageMode=SD, resolution=PREVIEW, lines=48, bytes=3072)) - t(sunCamMgr.DOWNLOAD sent) <= 10 s
- L2-5: t(event sunCamMgr.DownloadComplete(slot=SLOT_0, imageMode=SD, resolution=FULL, lines=480, bytes=307200)) - t(sunCamMgr.DOWNLOAD sent) <= 90 s; event sunCamMgr.LineRetry count <= 4
- L2-10: t(event sunCamMgr.DownloadComplete(slot=SLOT_0, imageMode=HD, resolution=PREVIEW, lines=192, bytes=12288)) - t(sunCamMgr.DOWNLOAD sent) <= 40 s
- L2-11: t(event sunCamMgr.DownloadComplete(slot=SLOT_3, imageMode=SD, resolution=PREVIEW, lines=48, bytes=3072)) - t(sunCamMgr.DOWNLOAD sent) <= 10 s

## 6 Fault menu
Generated from `planted_faults.py` planted fault declarations (`fth planted-faults-menu`): expect_wrong_exposure_push (stimulus; L2-6); expect_wrong_exposure_resetup (stimulus; L2-1); preview_instead_of_full (stimulus; L2-5); read_wrong_register (stimulus; L2-8); sleep_before_final (uut-state; L7-1).

## 7 Not covered
- REQ-004/016/018 (timeout, failed set-up step, failed line), REQ-020 (stray bytes, power-on line — SDD §Hardware notes), REQ-021 (mode mismatch), REQ-034 (camera restart while READY: needs a camera power cycle), REQ-024 (send/allocation failure), REQ-028 (readback mismatch), REQ-029 (queue full): no plantable mechanism on this bench (no power control, no fault injector, no second bus writer) — unit tests.
- HD FULL download: four slots of the same 480-line shape as SD FULL (L2-5), 1920 lines ≈ 2 min; the bench exercises the HD PREVIEW four-quadrant product (L2-10). ZOOM mode: framing identical to SD, not run on the bench (the FOV crop is the camera's). Memory Status and camera-side parameter errors are not available on this hardware (SDD §Hardware notes) and are not tested. A rejected HD slot (REQ-035) is unit-tested only. Camera error reply (REQ-019): no documented command this unit answers with an error reply (SDD §Hardware notes, Camera-side parameter validation), so REQ-019 is Unit Test only and has no bench test.

## 8 Decision log
24. 2026-11-09 designer — HUMAN GATE-4 nits: the Capture ACK is 0-byte only (REQ-013; any other payload length is MALFORMED → ReplyTimeout → EXECUTION_ERROR), REQ-033 reports the Exposure channel value; REQ-036 "Capture shall be sent only while READY" mapped to L6-1 (CAPTURE NOT_READY, RXV unchanged) and L8-1; block diagram and unit-test list (testNoCaptureWhenNotSetup) follow. No test procedure or check changed.
23. 2026-11-09 designer — HUMAN RULING: one human-in-the-loop run-for-record test. L8-1 added: SLEEP to NOT_SETUP, human power-cycles the camera at the runner's prompt (`human_step`, `run_in: ["rfr"]`; fth v0.1.4 fields), then SETUP_CAMERA; checks the one 21-byte FrameDiscarded(MALFORMED, 21), no CameraRestarted, SetupComplete(SD, 672), READY. START is marked before the human step so the power-on line falls inside the window. Covers REQ-003/-020/-034 (tolerance side); REQ-034 detection side stays unit test. Deferred for all but the run-for-record.
22. 2026-11-09 designer — reopen-review fixes: L6-1 loses the MEMORY_STATUS step (NOT_READY 3, OpCodeError 4); L2-10 asserts the REQ-027 exposure re-push after each mode change (SettingApplied(EXPOSURE, 672) 2, ExposureReadback 2); REQ-019 verification Unit Test; REQ-034 is now camera-restart detection (power-on line while READY → NOT_SETUP), waived on the bench pending a software power-cycle port; rationales cite SDD §Hardware notes rows or the design record (gate package) + runs/probes-5.log instead of bare H-numbers.
21. 2026-11-09 designer — probes-5 applied: Mode {SLEEP 0, SD 1, ZOOM 2, HD 3} (the earlier "HD" probes had sent mode byte 2 = Zoom); slots are 0–3 in every frame (index 4 aliases slot 1 — never emitted), so every SLOT_n in this plan is renumbered n−1; HD (mode 3) is one 1280×960 image across slots 0..3 as quadrants, so L2-10 becomes the HD capture + PREVIEW download of the four-quadrant product (192 records, 128×96 PNG, slot-tagged quadrant placement in `assemble`), DOWNLOAD/CAPTURE in HD with SLOT_0 only (REQ-035, unit test); exposure resets on every mode change (REQ-027 rationale); L5-2 stays dropped; `memory_slot_exposure` helper removed with MemorySlots. 18 tests, 5 planted faults (fails strings follow the renumbering).
20. 2026-11-09 designer — SDD ruling applied: MEMORY_STATUS removed from the component (unimplemented feature, Rev 1.3 §7.4.3), so L5-2 (its CameraError stimulus) is dropped; REQ-019 becomes Unit Test + Inspection — the unit answers every documented command with a normal frame (H4) and no other camera-error stimulus is known (candidate: Capture while in Sleep, error type 3, to be probed). REQ-032 (withdrawn) removed from the requirements map; REQ-034 (power-on line tolerance, unit test only) added. SDD §Not supported on our hardware is now §Hardware notes; citations follow. 18 tests, 5 planted faults unchanged.
19. 2026-11-09 designer — datasheet input corrected to KissCAM V2 Rev 1.3 (May 2025; Rev 1.2 May 2024 is the point of change, Rev 1.1 superseded). Rev 1.3 confirms H1 (§7.4.3 Memory Status "not currently implemented") and H2 (§7.4.5 response figure `40 43 MD 00 00 0D`, 0 telemetry bytes; its prose still says two) — rationales now cite Rev 1.3; L5-2's MEMORY_STATUS stimulus is settled (KEEP). Rev 1.3 modes are 0 Sleep, 1 SD, 2 Zoom, 3 HD: our "HD" probes sent mode byte 2 (= Zoom), so H5 and L2-10's mode semantics are re-measured by probes-5 (phase C); L2-10 unchanged until then. Preview 64×48 vs the datasheet's 80×60 (all revisions) stays a hardware discrepancy. No test, check or planted fault changed.
18. 2026-11-09 designer — H7 power-on banner ('MVP Camera V2 RS422\r\n', 21 unframed bytes captured by the orchestrator while the human power-cycled the camera): REQ-020 reworded to cover bytes outside a frame, unit test testPowerOnBanner added; no system test — the stimulus needs a camera power cycle, which the bench procedure reserves to the human (no hub power cycling); UT-only waiver recorded here and in not_covered.
17. 2026-11-09 designer — plan reopen-2 dispositions (hardware-true): N1 planted_faults.py decode path to bench geometry (PREVIEW 64 px, ImageHeader >BBBHHHH with exposure, no cameraMode, single-slot assembly for SD and HD; helper arg exposure=672); N2 planted_faults.py fails/mechanism strings moved to the L7-1/L2-5 constants and faults-menu.json regenerated with `fth planted-faults-menu` (never hand-edited again); N3 L2-4 LinesDownloaded == 48 and texts; N4 DownloadComplete.bytes = image bytes received (lines × 640 / × 64) — SDD Behavior, Events row and FPP doc-comment state the unit; plan literals 3072 / 307200 stand. C1 refresh gate 6 reworded (H5); C2 CameraError count == 0 in L2-4/L2-5/L2-10/L7-1 (no exact Exchanges delta: REQ-016 retries); C3 unit-test list keyed testDownloadHdSingleSlot; C4 L2-10 keep/withdraw paragraph in SDD §Not supported. Requirements reopen-5 split REQ-013 → REQ-033 (Capture exposure reporting): covered by L2-3 and L2-10. Mode B step 3b: KAT for the decode helper (synthetic 64×48 and 640×480 containers) is owed by the harness child.
17. 2026-11-09 designer — design reopen (hardware-true, HUMAN RULING "it must be functional on the hardware we have"): Memory Status not implemented on the unit (H1) → removed from L2-3/L2-4/L2-5/L5-1/L2-10/L7-1, MEMORY_STATUS kept standalone as the camera-error stimulus of L5-2 (CameraError UNRECOGNISED_COMMAND, replaces READ_REGISTER 0xFFFF which the camera answers, H4); preview = 64×48 (H3): L2-4/L7-1 lines=48 bytes=3072, PNG 64×48; HD = single slot tagged HD (H5): L2-10 downloads slot 1, 48 lines, 64×48; REQ-032 withdrawn (hardware); L2-8 SettingApplied(EXPOSURE, 672) count 2 (set-up push + explicit push); L2-9 ModeMismatch == 0 declared once (ABS). faults-menu: names unchanged; sleep_before_final `fails` follow the L7-1 constants (lines=48, bytes=3072, 64×48) and lose the MemoryStatusReply check; preview_instead_of_full mechanism text 48 lines / 3072 bytes.
1. 2026-11-06 designer — deployment = SunCamRef in fprime-devices-reference (human-directed in the request; repository was empty). Test deployment in the contract's sense.
2. 2026-11-06 designer — marker = cmdDisp.CMD_NO_OP_STRING / NoOpStringReceived, format `Received a NO-OP string={}` read from Svc/CmdDispatcher/CmdDispatcher.fpp (id 8); probe id reserved_min − 1. L0 desk-checked; bench confirmation at stage 2.
3. 2026-11-06 designer — decoded image evidence (request): the bench dump copies the DpWriter directory into record/raw/dp/ (hashed record); helper decode_image_in_window selects the product by container id and window time, FAILs when absent, writes dev-evidence/images/<test>.png; dev-evidence/README.md lists the PNGs so `fth package` links them in the QL.
4. 2026-11-06 designer — coverage targets ut 95 / system 75 (skill baselines); not_covered_ack lists the camera-side fault paths.
5. 2026-11-07 designer (review round 1) — one planted-fault declaration per plant site, no empty ripples: expect_wrong_exposure_resetup@L2-1 (W2, stateless rewrite), expect_wrong_exposure_push@L2-6, read_wrong_register@L2-8 (stimulus: the drive of the operation under test is changed — the skill's harness-expectation class fits a rewritten verification step, which this protocol does not have), preview_instead_of_full@L2-5, sleep_before_final@L7-1 (uut-state); max_count 2; 5 drawable tests ≥ 2 × max_count. L5-1 (REQ-009/-017) and L5-3 (REQ-011) carry no fault so no draw leaves a requirement uncovered; REQ-012/-023 gained the fault-free L2-9.
6. 2026-11-07 designer (review round 1) — cmdDisp.OpCodeError is a UUT fact (every non-OK response): removed from STD, asserted per test with the expected count.
7. 2026-11-07 designer (review round 1) — telemetry observability: the design re-writes the suncam packet channels at 1 Hz and on change (SDD §Behavior, design reopen); camera-sourced channels are write-on-reply (channels_note).
8. 2026-11-07 designer (review round 1) — EXPOSURE is not range-checked by the component (SDD Table 1, design reopen): the camera's error reply is the single validator, which makes REQ-011/REQ-019 testable on the bench (L5-3).
9. 2026-11-07 designer (review round 1, design reopen) — RegisterRead prints address 0x{x} (operator/datasheet convention, design reviewer) and value decimal: the asserted literals (3012, 300/672) contain no hex letters and are case-independent; the §7 refresh confirms every pattern against the SunCamRef dictionary.
16. 2026-11-09 designer — plan reopen 1: NumDataProducts restarts with SunCamRef at L3-1 (L5-1 → 1, L7-1 → 2); L2-10 re-captures SD into all four slots and checks Memory Status so later tests never depend on how the camera reports a partial HD overwrite; L5-3 shows the set-up-clears-pending-push choice (SettingApplied/Readback 672 once) and the camera's RXV (+6); refresh set updated; duplicate ABS member dropped.
15. 2026-11-09 designer — requirements reopen 4: REQ-031 reworded (refused push, READY kept; set-up failure is REQ-004 alone), REQ-032 added (no SD image / incomplete HD → DownloadFailed(NO_IMAGE), UT); architecture reopen: Behavior split into a Tick-path paragraph, empty-slot branch named.
14. 2026-11-09 designer — HUMAN RULING at the SDD gate (ledger 18): EXPOSURE range-checked by the component (L5-3 re-derived: SettingRejected + local SetupFailed(SET_EXPOSURE, OUT_OF_RANGE), covering REQ-004/-031 on the bench; REQ-011 back to UT); one data product per IMAGE (DOWNLOAD runs Memory Status first; HD = four quadrant slots in one product; new L2-10 HD preview product; DownloadStarted/Complete carry imageMode; product count order 1..5); DownloadAborted ACTIVITY_HI (commanded) vs DownloadFailed WARNING_HI (ABS gains DownloadFailed == 0); `run` is a sync port with an atomic + internal hook port (unit test testRunPortSingleQueuedTick; the plan's RUN_TICK overflow source is unchanged).
13. 2026-11-07 designer — round-3 dispositions: C1 REQ-030 covered by the quiet windows L0-1/L0-2 (period itself UT); C2 the §7-refresh set is listed in entry gates / decision log 10 and shown to the human at the gate. Plan review closed: 0 must fix.
12. 2026-11-07 designer — round-2 dispositions: N1 LibraryVersions format plural + file:line sources; N2 STD/ABS in every window list, checks_note, R window requires markers only; C1 fpp cited; C2 enum values in SDD Table 1 (requirements reopen); C3 W2 duplicate dropped, repeats noted; C4 stateless rewrite fault expect_wrong_exposure_resetup (L2-1 W2 push 300→299); C5 L5-3 fallback + CameraMode check; C6 preview expectation reduced to header + ordered lines, KAT at refresh; C7 L6-2 RXV bracket; C8 wording; C9 read_wrong_register reclassed stimulus; C10 count literal dropped, helper asserts the manifest count. REQ-030 (requirements reopen) added as a UT waiver. No disagreements.
11. 2026-11-07 designer — round-1 dispositions: must-fix M1–M15 all applied (M1 OpCodeError per test; M2 periodic channels + channels_note; M3 marker format; M4 Version payload helper + LibraryVersions; M5 three-window L3-1 with the reset inside R; M6 no window suffixes, one check list per window; M7 dpMgr.NumDataProducts; M8 product files in record/raw/dp + window-bound helper; M9/M10/M14 one declaration per plant site, complete verbatim fails, kinds; M11 fault-free L5-1/L5-3 and new L2-9; M12 L2-9 + L2-7 CAPTURE rejection; M13 shared-edge windows; M15 RXF as delta). Could-fix applied: C1–C8, C10–C18; C9 applied as reclass to stimulus plus the harness-expectation fault read_wrong_register (L2-8). No disagreements.
10. 2026-11-07 designer (review rounds 1–2) — the §7.4.5 test pattern has no textual generator and its 80×60 preview decimation is unspecified: the preview helpers check header + 60 ordered lines only; a pinned reference (KAT, expect=pattern_kat) is added at the §7 refresh from the first bench preview — a plan change the human sees once.
25. 2026-11-09 anchor — HUMAN RULING (P-1, Mode B round 1): L8-1 window W no longer applies the ABS group as a whole (its member `FrameDiscarded count == 0` contradicted the explicit `FrameDiscarded(cause=MALFORMED, bytes=21) count == 1`); W lists the other ABS members explicitly. No other pass-rule change.
27. 2026-11-12 anchor (campaign suncam-v2, DOWNLOAD priority argument, REQ-SunCamMgr-037) — DOWNLOAD takes a third argument priority: every existing procedure passes 0 (configured priority; the products are unchanged), new L2-11 passes 7; decode_image_in_window gains an optional `priority` argument checked in L2-4 (10) and L2-11 (7). No other test, check or planted fault changes.
