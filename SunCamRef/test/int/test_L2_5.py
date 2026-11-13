"""L2-5: Full download → Image data product (decoded)

Procedure (plan.json, verbatim order):
  MARK(250)
  bracket (2 suncam samples)
  sunCamMgr.DOWNLOAD(SLOT_0, FULL, 0)
  wait(DownloadComplete, 120 s)
  bracket (2 suncam samples)
  MARK(251)
"""
import pytest

from suncam import bracket, helper, wait_any


@pytest.mark.req('REQ-SunCamMgr-014')
def test_L2_5(fth_plan, window, check, require, send, bench):
    with window(250, 251):  # W
        require("STD")
        check('event sunCamMgr.DownloadStarted(slot=SLOT_0, imageMode=SD, resolution=FULL, lines=480) count == 1')
        check('event sunCamMgr.DownloadComplete(slot=SLOT_0, imageMode=SD, resolution=FULL, lines=480, bytes=307200) count == 1')
        check('event sunCamMgr.DownloadAborted count == 0')
        check('delta(sunCamMgr.LinesDownloaded) == 480')
        check('delta(sunCamMgr.ProductsSent) == 1')
        check('last(dpMgr.NumDataProducts) == 2')
        check('one Image product in window: ImageHeader(slot=0, imageMode=SD, resolution=FULL, width=640, height=480, exposure=672), 480 slot-tagged ImageLine records in order; PNG → dev-evidence/images/L2-5-full.png',
              helper(fth_plan, "decode_image_in_window", slot=0, image_mode='SD', resolution='FULL', width=640, height=480, lines=480, expect='none', out='L2-5-full.png', exposure=672))
        check('event sunCamMgr.CameraError count == 0')
        check('event cmdDisp.OpCodeError count == 0')
        check('ABS')
        bracket(bench)
        send("sunCamMgr.DOWNLOAD", ['SLOT_0', 'FULL', '0'])
        bench.wait_event("sunCamMgr.DownloadComplete", 120)
        bracket(bench)
