"""L2-4: Preview download → Image data product (decoded)

Procedure (plan.json, verbatim order):
  MARK(240)
  bracket (2 suncam samples)
  sunCamMgr.DOWNLOAD(SLOT_3, PREVIEW, 0)
  wait(DownloadComplete, 20 s)
  bracket (2 suncam samples)
  MARK(241)
"""
import pytest

from suncam import bracket, helper, wait_any


@pytest.mark.req('REQ-SunCamMgr-001', 'REQ-SunCamMgr-014', 'REQ-SunCamMgr-015', 'REQ-SunCamMgr-037')
def test_L2_4(fth_plan, window, check, require, send, bench):
    with window(240, 241):  # W
        require("STD")
        check('event sunCamMgr.DownloadStarted(slot=SLOT_3, imageMode=SD, resolution=PREVIEW, lines=48) count == 1')
        check('event sunCamMgr.DownloadComplete(slot=SLOT_3, imageMode=SD, resolution=PREVIEW, lines=48, bytes=3072) count == 1')
        check('event sunCamMgr.LineRetry count == 0')
        check('event sunCamMgr.DownloadAborted count == 0')
        check('delta(sunCamMgr.LinesDownloaded) == 48')
        check('delta(sunCamMgr.ProductsSent) == 1')
        check('last(dpMgr.NumDataProducts) == 1')
        check('exactly one Image product in record/raw/dp/ with header time in [t(START), t(END)]: ImageHeader(slot=3, imageMode=SD, resolution=PREVIEW, width=64, height=48, exposure=672) with container priority 10, 48 slot-tagged ImageLine records in order; PNG → dev-evidence/images/L2-4-preview.png',
              helper(fth_plan, "decode_image_in_window", slot=3, image_mode='SD', resolution='PREVIEW', width=64, height=48, lines=48, expect='none', out='L2-4-preview.png', exposure=672, priority=10))
        check('event sunCamMgr.CameraError count == 0')
        check('event cmdDisp.OpCodeError count == 0')
        check('ABS')
        bracket(bench)
        send("sunCamMgr.DOWNLOAD", ['SLOT_3', 'PREVIEW', '0'])
        bench.wait_event("sunCamMgr.DownloadComplete", 20)
        bracket(bench)
