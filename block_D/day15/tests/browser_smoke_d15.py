"""Chromium/Chrome smoke: actual JS prediction/reveal/fault interaction at 1920x1080.
No network dependency; no ROS/Gazebo/Goal. Skips with explicit NOT_RUN when missing.
"""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import struct

DAY=Path(__file__).resolve().parents[1]
def main():
    browser=next((shutil.which(x) for x in ("google-chrome","google-chrome-stable","chromium","chromium-browser") if shutil.which(x)),None)
    if browser is None:
        print("D15_BROWSER_NOT_RUN_CHROME_NOT_INSTALLED")
        return 0
    with tempfile.TemporaryDirectory(prefix="axia_d15_chrome_") as tmp:
        out=Path(tmp)
        run=subprocess.run([sys.executable,str(DAY/"run_lab.py"),"--out",str(out)],
                           capture_output=True,text=True,timeout=20)
        if run.returncode:
            print("D15_BROWSER_CLI_FAILED",run.stdout,run.stderr)
            return 2
        p=out/"d15_offline_replay.html"
        html=p.read_text(encoding="utf-8")
        smoke="""<div id="browserSmokeResult">PENDING</div><script>
(function(){
let d=document, sel=d.getElementById('predict');sel.value='1';
sel.dispatchEvent(new Event('change',{bubbles:true}));
d.getElementById('reveal').click();
let exposed=!d.getElementById('evidencePanel').hidden;
let distance=d.getElementById('distanceValue').textContent.includes('2.025');
d.getElementById('next').click();
let advanced=d.getElementById('stageLabel').textContent==='SLOW';
d.getElementById('faultCase').value='0';
d.getElementById('faultGuess').value='scan_gap_max_ms';
d.getElementById('checkFault').click();
let fault=d.getElementById('faultResult').textContent.includes('정답!');
d.getElementById('browserSmokeResult').textContent=
  exposed&&distance&&advanced&&fault?'BROWSER_SMOKE_PASS':'BROWSER_SMOKE_FAIL '+[exposed,distance,advanced,fault].join(',');
})();
</script>"""
        p.write_text(html.replace("</body>",smoke+"</body>"),encoding="utf-8")
        png=out/"evidence_theater_1920.png"
        cmd=[browser,"--headless","--no-sandbox","--disable-gpu",
             "--disable-dev-shm-usage","--hide-scrollbars",
             "--window-size=1920,1080","--virtual-time-budget=2000",
             "--screenshot="+str(png),"--dump-dom",p.as_uri()]
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=40)
        if cp.returncode!=0 or "BROWSER_SMOKE_PASS" not in cp.stdout:
            print("D15_BROWSER_SMOKE_FAIL rc="+str(cp.returncode))
            print(cp.stdout[-3000:]);print(cp.stderr[-2200:])
            return 3
        if png.is_file():
            b=png.read_bytes()
            if len(b)<24 or not b.startswith(b"\x89PNG\r\n\x1a\n"):
                print("D15_BROWSER_BAD_SCREENSHOT");return 4
            width,height=struct.unpack(">II",b[16:24])
            print(f"D15_BROWSER_SCREENSHOT={width}x{height}")
            if width<1366 or height<768:
                print("D15_BROWSER_SCREENSHOT_TOO_SMALL");return 5
        else:
            print("D15_BROWSER_SCREENSHOT_NOT_CREATED")
            return 6
        print("D15_BROWSER_SMOKE_PASS_PREDICT_REVEAL_NEXT_FAULT_SCOPE_NO_ROS_GAZEBO")
        return 0
if __name__=="__main__":
    raise SystemExit(main())
