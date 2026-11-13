"""L6-1: Negative control: READY-only commands refused while NOT_SETUP

Procedure (plan.json, verbatim order):
  MARK(610)
  bracket (2 suncam samples)
  sunCamMgr.SLEEP
  wait(SleepEntered, 5 s)
  bracket (2 suncam samples)
  MARK(612)
  bracket (2 suncam samples)
  sunCamMgr.PING(MCU)
  wait(PingReply, 5 s)
  sunCamMgr.CAPTURE(SLOT_0, OFF)
  sunCamMgr.DOWNLOAD(SLOT_0, PREVIEW, 0)
  sunCamMgr.READ_REGISTER(12306)
  sunCamMgr.DOWNLOAD_ABORT
  wait(2 s)
  sunCamMgr.PING(MCU)
  wait(PingReply, 5 s)
  bracket (2 suncam samples)
  MARK(611)
"""
import pytest

from suncam import bracket, helper, wait_any


@pytest.mark.req('REQ-SunCamMgr-002', 'REQ-SunCamMgr-007', 'REQ-SunCamMgr-008', 'REQ-SunCamMgr-026', 'REQ-SunCamMgr-036')
def test_L6_1(fth_plan, window, check, require, send, bench):
    with window(610, 612):  # W1
        require("STD")
        check('event sunCamMgr.SleepEntered count == 1')
        check('last(sunCamMgr.SetupState) == NOT_SETUP')
        check('event cmdDisp.OpCodeError count == 0')
        check('ABS')
        bracket(bench)
        send("sunCamMgr.SLEEP", [])
        bench.wait_event("sunCamMgr.SleepEntered", 5)
        bracket(bench)
    with window(612, 611):  # W
        require("STD")
        check('event sunCamMgr.CommandRejected(cause=NOT_READY) count == 3')
        check('event sunCamMgr.CommandRejected(operation=DOWNLOAD_ABORT, cause=NO_DOWNLOAD) count == 1')
        check('event sunCamMgr.PingReply(pingType=MCU) count == 2')
        check('delta(sunCamMgr.Exchanges) == 2')
        check('CameraValidCmds advances by exactly 1 between the two ping replies: no refused command reached the camera (mod 256)',
              helper(fth_plan, "delta_mod", channel='sunCamMgr.CameraValidCmds', delta=1, mod=256))
        check('delta(sunCamMgr.ImagesCaptured) == 0')
        check('delta(sunCamMgr.ProductsSent) == 0')
        check('last(sunCamMgr.SetupState) == NOT_SETUP')
        check('event cmdDisp.OpCodeError count == 4')
        check('ABS')
        bracket(bench)
        send("sunCamMgr.PING", ['MCU'])
        bench.wait_event("sunCamMgr.PingReply", 5)
        send("sunCamMgr.CAPTURE", ['SLOT_0', 'OFF'], wait_completion=False)  # plan expects the UUT to refuse this command (OpCodeError)
        send("sunCamMgr.DOWNLOAD", ['SLOT_0', 'PREVIEW', '0'], wait_completion=False)  # plan expects the UUT to refuse this command (OpCodeError)
        send("sunCamMgr.READ_REGISTER", [12306], wait_completion=False)  # plan expects the UUT to refuse this command (OpCodeError)
        send("sunCamMgr.DOWNLOAD_ABORT", [], wait_completion=False)  # plan expects the UUT to refuse this command (OpCodeError)
        bench.wait(2)
        send("sunCamMgr.PING", ['MCU'])
        bench.wait_event("sunCamMgr.PingReply", 5)
        bracket(bench)
