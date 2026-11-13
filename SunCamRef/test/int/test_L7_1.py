"""L7-1: Final state: test-pattern capture, preview product on disk

Procedure (plan.json, verbatim order):
  MARK(710)
  bracket (2 suncam samples)
  sunCamMgr.CAPTURE(SLOT_3, ON)
  wait(CaptureComplete, 10 s)
  sunCamMgr.DOWNLOAD(SLOT_3, PREVIEW, 0)
  wait(DownloadComplete, 20 s)
  bracket (2 suncam samples)
  MARK(711)
"""
import pytest

from suncam import bracket, helper, wait_any


@pytest.mark.req('REQ-SunCamMgr-001', 'REQ-SunCamMgr-013', 'REQ-SunCamMgr-015')
def test_L7_1(fth_plan, window, check, require, send, bench):
    with window(710, 711):  # W
        require("STD")
        check('event sunCamMgr.CaptureComplete(slot=SLOT_3, testPattern=ON, mode=SD) count == 1')
        check('event sunCamMgr.DownloadComplete(slot=SLOT_3, imageMode=SD, resolution=PREVIEW, lines=48, bytes=3072) count == 1')
        check('event sunCamMgr.CommandRejected count == 0')
        check('delta(sunCamMgr.ImagesCaptured) == 1')
        check('delta(sunCamMgr.ProductsSent) == 1')
        check('last(dpMgr.NumDataProducts) == 2')
        check('last(sunCamMgr.SetupState) == READY')
        check('exactly one Image product in window: ImageHeader(slot=3, imageMode=SD, resolution=PREVIEW, width=64, height=48, exposure=672), 48 lines in order; PNG → dev-evidence/images/L7-1-final.png',
              helper(fth_plan, "decode_image_in_window", slot=3, image_mode='SD', resolution='PREVIEW', width=64, height=48, lines=48, expect='none', out='L7-1-final.png', exposure=672))
        check('event sunCamMgr.CameraError count == 0')
        check('event cmdDisp.OpCodeError count == 0')
        check('ABS')
        bracket(bench)
        send("sunCamMgr.CAPTURE", ['SLOT_3', 'ON'])
        bench.wait_event("sunCamMgr.CaptureComplete", 10)
        send("sunCamMgr.DOWNLOAD", ['SLOT_3', 'PREVIEW', '0'])
        bench.wait_event("sunCamMgr.DownloadComplete", 20)
        bracket(bench)
