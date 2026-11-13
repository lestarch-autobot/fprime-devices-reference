"""L5-1: Busy rejection and commanded download abort

Procedure (plan.json, verbatim order):
  MARK(510)
  bracket (2 suncam samples)
  sunCamMgr.DOWNLOAD(SLOT_0, FULL, 0)
  wait(DownloadStarted, 5 s)
  sunCamMgr.PING(MCU)
  wait(CommandRejected, 5 s)
  sunCamMgr.DOWNLOAD_ABORT
  wait(DownloadAborted, 10 s)
  bracket (2 suncam samples)
  MARK(511)
"""
import pytest

from suncam import bracket, helper, wait_any


@pytest.mark.req('REQ-SunCamMgr-009', 'REQ-SunCamMgr-017')
def test_L5_1(fth_plan, window, check, require, send, bench):
    with window(510, 511):  # W
        require("STD")
        check('event sunCamMgr.DownloadStarted(slot=SLOT_0, imageMode=SD, resolution=FULL, lines=480) count == 1')
        check('event sunCamMgr.CommandRejected(operation=PING, cause=BUSY) count == 1')
        check('event sunCamMgr.DownloadAborted(slot=SLOT_0) count == 1')
        check('event sunCamMgr.DownloadComplete count == 0')
        check('event sunCamMgr.PingReply count == 0')
        check('delta(sunCamMgr.ProductsSent) == 1')
        check('last(dpMgr.NumDataProducts) == 1')
        check('last(sunCamMgr.CurrentOperation) == NONE')
        check('last(sunCamMgr.SetupState) == READY')
        check('event cmdDisp.OpCodeError count == 1')
        check('ABS')
        bracket(bench)
        send("sunCamMgr.DOWNLOAD", ['SLOT_0', 'FULL', '0'], wait_completion=False)  # completes when the operation ends; the plan waits on its Started event
        bench.wait_event("sunCamMgr.DownloadStarted", 5)
        send("sunCamMgr.PING", ['MCU'], wait_completion=False)  # plan expects the UUT to refuse this command (OpCodeError)
        bench.wait_event("sunCamMgr.CommandRejected", 5)
        send("sunCamMgr.DOWNLOAD_ABORT", [])
        bench.wait_event("sunCamMgr.DownloadAborted", 10)
        bracket(bench)
