"""L2-11: Preview download with commanded priority → Image product priority 7

Procedure (plan.json, verbatim order):
  MARK(2110)
  bracket (2 suncam samples)
  sunCamMgr.DOWNLOAD(SLOT_3, PREVIEW, 7)
  wait(DownloadComplete, 20 s)
  bracket (2 suncam samples)
  MARK(2111)
"""
import pytest

from suncam import bracket, helper, wait_any


@pytest.mark.req('REQ-SunCamMgr-037')
def test_L2_11(fth_plan, window, check, require, send, bench):
    with window(2110, 2111):  # W
        require("STD")
        check('event sunCamMgr.DownloadStarted(slot=SLOT_3, imageMode=SD, resolution=PREVIEW, lines=48) count == 1')
        check('event sunCamMgr.DownloadComplete(slot=SLOT_3, imageMode=SD, resolution=PREVIEW, lines=48, bytes=3072) count == 1')
        check('event sunCamMgr.DownloadAborted count == 0')
        check('delta(sunCamMgr.LinesDownloaded) == 48')
        check('delta(sunCamMgr.ProductsSent) == 1')
        check('last(dpMgr.NumDataProducts) == 4')
        check('one Image product in window: ImageHeader(slot=3, imageMode=SD, resolution=PREVIEW, width=64, height=48, exposure=672) with container priority 7, 48 slot-tagged ImageLine records in order; PNG → dev-evidence/images/L2-11-preview-priority.png',
              helper(fth_plan, "decode_image_in_window", slot=3, image_mode='SD', resolution='PREVIEW', width=64, height=48, lines=48, expect='none', out='L2-11-preview-priority.png', exposure=672, priority=7))
        check('event sunCamMgr.CameraError count == 0')
        check('event cmdDisp.OpCodeError count == 0')
        check('ABS')
        bracket(bench)
        send("sunCamMgr.DOWNLOAD", ['SLOT_3', 'PREVIEW', '7'])
        bench.wait_event("sunCamMgr.DownloadComplete", 20)
        bracket(bench)
