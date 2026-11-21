'use strict';
/* Chromium CDP smoke: actual file:// browser interactions + 1920x1080 render.
   No npm dependencies; intentionally no ROS, Gazebo, network service or robot.
*/
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const cp=require('node:child_process');
const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');

const page=path.resolve(__dirname,'../day12/incident_command_center/AXIA_D12_INCIDENT_COMMAND_CENTER.html');
const fixture=path.resolve(__dirname,'../day12/ros_transport/sample_events.jsonl');
const out=path.resolve(__dirname,'../../results/block-c-student/d12-browser-qa');
fs.mkdirSync(out,{recursive:true});

const sleep=(ms)=>new Promise(resolve=>setTimeout(resolve,ms));
function chromeBinary(){
  for(const command of ['google-chrome','google-chrome-stable','chromium','chromium-browser']){
    try{const bin=cp.execFileSync('which',[command],{encoding:'utf8'}).trim();if(bin)return bin}catch{}
  }
  throw Error('D12_BROWSER_QA_BLOCKED_CHROMIUM_MISSING');
}
async function main(){
  const profile=fs.mkdtempSync(path.join(os.tmpdir(),'axia-d12-chrome-'));
  const chrome=cp.spawn(chromeBinary(),[
    '--headless=new','--no-sandbox','--disable-dev-shm-usage','--disable-gpu',
    '--no-first-run','--no-default-browser-check','--remote-allow-origins=*',
    '--remote-debugging-port=0','--window-size=1920,1080',
    '--user-data-dir='+profile,'about:blank'
  ],{stdio:'ignore'});
  let ws;
  try{
    let port=0;
    for(let i=0;i<120;i++){
      await sleep(100);
      if(chrome.exitCode!==null)throw Error('Chrome exited before debugger started: '+chrome.exitCode);
      try{port=Number(fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0]);if(port)break}catch{}
    }
    assert.ok(port,'D12_BROWSER_QA_NO_DEBUG_PORT');
    const tabs=await (await fetch('http://127.0.0.1:'+port+'/json/list')).json();
    const tab=tabs.find(x=>x.type==='page');
    assert.ok(tab&&tab.webSocketDebuggerUrl,'no page target');
    ws=new WebSocket(tab.webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})});
    const pending=new Map();
    let seq=0;
    const exceptions=[];
    ws.addEventListener('message',(ev)=>{
      const p=JSON.parse(String(ev.data));
      if(p.method==='Runtime.exceptionThrown')exceptions.push(p.params.exceptionDetails.text);
      if(p.id&&pending.has(p.id)){const t=pending.get(p.id);pending.delete(p.id);p.error?t.reject(Error(p.error.message)):t.resolve(p.result)}
    });
    async function send(method,params={}){
      const id=++seq;
      return await new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timeout '+method))},15000);
        pending.set(id,{resolve:(v)=>{clearTimeout(timer);resolve(v)},reject:(e)=>{clearTimeout(timer);reject(e)}});
        ws.send(JSON.stringify({id,method,params}));
      });
    }
    async function evaluate(expr){
      const v=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});
      if(v.exceptionDetails)throw Error('Browser JavaScript exception: '+JSON.stringify(v.exceptionDetails));
      return v.result.value;
    }
    async function until(expr,seconds=10){
      for(let i=0;i<seconds*10;i++){if(await evaluate(expr))return;await sleep(100)}
      throw Error('Browser condition timeout: '+expr);
    }
    await send('Page.enable');
    await send('Runtime.enable');
    await send('Emulation.setDeviceMetricsOverride',{width:1920,height:1080,deviceScaleFactor:1,mobile:false});
    await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:out});
    await send('Page.navigate',{url:pathToFileURL(page).href});
    await until("document.readyState==='complete' && document.getElementById('toast') && document.getElementById('toast').textContent.includes('준비 완료')");
    assert.equal(await evaluate("document.getElementById('totalCount').textContent"),'12');
    assert.equal(await evaluate("document.getElementById('seenCount').textContent"),'0');
    assert.equal(await evaluate("document.getElementById('modeBadge').textContent.includes('SYNTHETIC REPLAY')"),true);
    assert.equal(await evaluate("document.documentElement.scrollWidth<=window.innerWidth+2"),true);
    const boxes=await evaluate("['timeline','detail','feedbackList'].map(id=>{const b=document.getElementById(id).getBoundingClientRect();return {id,w:b.width,h:b.height,x:b.x}})");
    assert.equal(boxes.length,3);
    assert.ok(boxes.every(b=>b.w>250&&b.h>40&&b.x>=0));
    await evaluate("document.getElementById('stepBtn').click();document.getElementById('stepBtn').click();document.getElementById('stepBtn').click()");
    assert.equal(await evaluate("document.getElementById('caseId').textContent"),'DEMO:TST_N_00:002');
    assert.equal(await evaluate("document.getElementById('caseLevel').textContent"),'미공개');
    await evaluate("document.getElementById('revealBtn').click()");
    assert.ok((await evaluate("document.getElementById('toast').textContent")).includes('먼저 상태'));
    await evaluate("document.getElementById('guessSelect').value='WARNING';document.getElementById('guessSelect').dispatchEvent(new Event('change'));document.getElementById('revealBtn').click()");
    assert.equal(await evaluate("document.getElementById('caseLevel').textContent"),'WARNING');
    assert.equal(await evaluate("document.getElementById('caseScore').textContent"),'0.90');
    await evaluate("document.getElementById('feedbackAction').value='INVESTIGATE';document.getElementById('feedbackReason').value='교육용 경고 점수가 기준보다 큼, 실물 고장은 미확인';document.getElementById('saveFeedbackBtn').click()");
    await evaluate("document.getElementById('stepBtn').click()");
    assert.equal(await evaluate("document.getElementById('caseId').textContent"),'DEMO:TST_N_00:003');
    await evaluate("document.getElementById('guessSelect').value='INSUFFICIENT_DATA';document.getElementById('guessSelect').dispatchEvent(new Event('change'));document.getElementById('revealBtn').click()");
    assert.equal(await evaluate("document.getElementById('caseScore').textContent"),'UNSCORED');
    assert.equal(await evaluate("document.getElementById('eventStream').scrollWidth<=document.getElementById('eventStream').clientWidth+2"),true,'feed must not clip diagnostic names horizontally');
    await evaluate("document.getElementById('feedbackAction').value='CHECK_QUALITY';document.getElementById('feedbackReason').value='교육용 점수 결측, 품질 사유 확인 필요';document.getElementById('saveFeedbackBtn').click()");
    assert.equal(await evaluate("document.getElementById('feedbackList').children.length"),2);
    // Save PNG after realistic two-case investigation.
    const ss=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,fromSurface:true});
    const img=Buffer.from(ss.data,'base64');
    assert.equal(img.readUInt32BE(16),1920);
    assert.equal(img.readUInt32BE(20),1080);
    fs.writeFileSync(path.join(out,'d12_1920x1080_live_demo.png'),img);
    await evaluate("document.getElementById('exportFeedbackBtn').click()");
    const dl=path.join(out,'operator_feedback.jsonl');
    for(let i=0;i<70&&!fs.existsSync(dl);i++)await sleep(100);
    assert.ok(fs.existsSync(dl),'exported JSONL missing');
    const records=fs.readFileSync(dl,'utf8').trim().split(/\r?\n/).map(JSON.parse);
    assert.equal(records.length,2);
    assert.ok(records.every(r=>r.control_authority===false));
    assert.equal(records[0].event_id,'DEMO:TST_N_00:002');
    assert.equal(records[1].event_id,'DEMO:TST_N_00:003');
    // Import downloaded file using real DOM File API, no network.
    const imported=await evaluate("(async()=>{const t="+JSON.stringify(fs.readFileSync(dl,'utf8'))+";const f=new File([t],'operator_feedback.jsonl',{type:'application/x-ndjson'});const d=new DataTransfer();d.items.add(f);const x=document.getElementById('importFeedback');x.files=d.files;x.dispatchEvent(new Event('change',{bubbles:true}));await new Promise(r=>setTimeout(r,100));return document.getElementById('toast').textContent})()");
    assert.ok(imported.includes('검증 통과: 2건'),imported);
    const importedEvents=await evaluate("(async()=>{const t="+JSON.stringify(fs.readFileSync(fixture,'utf8'))+";const f=new File([t],'sample_events.jsonl',{type:'application/x-ndjson'});const d=new DataTransfer();d.items.add(f);const x=document.getElementById('importEvents');x.files=d.files;x.dispatchEvent(new Event('change',{bubbles:true}));await new Promise(r=>setTimeout(r,120));return document.getElementById('toast').textContent})()");
    assert.ok(importedEvents.includes('12건 검증'),importedEvents);
    assert.equal(await evaluate("document.getElementById('seenCount').textContent"),'0');
    assert.ok(!exceptions.length,'browser exceptions: '+exceptions.join(','));
    console.log('D12_BROWSER_REAL_UI_PASS chrome=file:// width=1920 height=1080');
    console.log('D12_REPLAY_INTERACTION_PASS warning=002 quality=003 hidden_before_guess=true');
    console.log('D12_FEEDBACK_BROWSER_EXPORT_IMPORT_PASS count=2 no_control=true');
    console.log('D12_BROWSER_SCREENSHOT '+path.join(out,'d12_1920x1080_live_demo.png'));
  }finally{
    if(ws)try{ws.close()}catch{}
    chrome.kill('SIGTERM');
    await sleep(550);
    try{fs.rmSync(profile,{recursive:true,force:true,maxRetries:5,retryDelay:250})}catch{}
  }
}
main().catch(e=>{console.error('D12_BROWSER_QA_FAIL',e.stack||e);process.exitCode=1});
