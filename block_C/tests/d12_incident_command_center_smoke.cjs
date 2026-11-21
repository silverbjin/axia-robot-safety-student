'use strict';
// Offline deterministic replay contract; no npm packages, ROS, Gazebo or network.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('node:assert/strict');

const root = path.join(__dirname, '..');
const htmlFile = path.join(root, 'day12/incident_command_center/AXIA_D12_INCIDENT_COMMAND_CENTER.html');
const fixtureFile = path.join(root, 'day12/ros_transport/sample_events.jsonl');
const html = fs.readFileSync(htmlFile, 'utf8');
const match = html.match(/<script>\s*([\s\S]+?)\s*<\/script>/i);
assert.ok(match, 'one embedded JavaScript block');
new vm.Script(match[1], { filename: htmlFile });
const ctx = vm.createContext({ console, Date, JSON, Set, Map });
vm.runInContext(match[1], ctx, { timeout: 3000 });
const api = ctx.AXIA_D12_TEST_API;
assert.ok(api && api.makeSampleEvents && api.parseEventJSONL && api.makeFeedbackRecord);

const original = fs.readFileSync(fixtureFile, 'utf8');
const fixture = api.parseEventJSONL(original);
const embedded = api.makeSampleEvents();
assert.equal(fixture.length, 12);
assert.equal(embedded.length, 12);
for(let i=0;i<12;i++) {
  // Equal contracts, no private IF/AE reference hidden in the replay.
  assert.deepEqual(JSON.parse(JSON.stringify(embedded[i])), JSON.parse(JSON.stringify(fixture[i])));
  assert.equal(embedded[i].control_authority, false);
  assert.equal(embedded[i].certified_estop, false);
  assert.equal(embedded[i].source, 'SYNTHETIC_COURSE_FIXTURE');
  assert.equal(embedded[i].model_id, 'EDUCATION_TRANSPORT_DEMO');
}
const distribution = api.countLevels(fixture);
assert.equal(distribution.NORMAL, 3);
assert.equal(distribution.CAUTION, 3);
assert.equal(distribution.WARNING, 3);
assert.equal(distribution.INSUFFICIENT_DATA, 3);
assert.equal(fixture[2].event_id, 'DEMO:TST_N_00:002');
assert.equal(fixture[2].risk_score, 0.9);
assert.equal(fixture[3].event_id, 'DEMO:TST_N_00:003');
assert.equal(fixture[3].risk_score, null);
assert.equal(fixture[3].threshold, null);

assert.throws(() => api.parseEventJSONL(original + original.split('\n')[0] + '\n'));
assert.throws(() => api.parseEventJSONL(original.replace('"control_authority": false','"control_authority": true')));
assert.throws(() => api.parseEventJSONL(original.replace('"risk_score": null','"risk_score": 0.0')));

const ts = '2026-11-21T03:00:00.000Z';
const a = api.makeFeedbackRecord(fixture[2], 'INVESTIGATE', '점수 0.90 > 기준 0.50, 원인 추가 조사', ts);
const b = api.makeFeedbackRecord(fixture[3], 'CHECK_QUALITY', '데이터 누락, 원인 확인 필요', ts);
assert.equal(a.control_authority, false);
assert.equal(b.event_id, 'DEMO:TST_N_00:003');
const feedbackText = api.serializeFeedback([a,b],fixture);
const parsed = api.parseFeedbackJSONL(feedbackText,fixture);
assert.equal(parsed.length,2);
assert.equal(parsed[0].reason,a.reason);
assert.equal(parsed[1].operator_action,'CHECK_QUALITY');
assert.throws(() => api.makeFeedbackRecord(fixture[2], 'STOP_ROBOT', '잘못된 명령',ts));
assert.throws(() => api.makeFeedbackRecord(fixture[2], 'INVESTIGATE','',ts));
assert.throws(() => api.parseFeedbackJSONL(feedbackText+feedbackText,fixture));
assert.throws(() => api.parseFeedbackJSONL(feedbackText.replace('"control_authority":false','"control_authority":true'),fixture));

console.log('D12_LIVE_REPLAY_CORE_GREEN events=12 levels=3/3/3/3 warning=002 quality=003');
console.log('D12_FEEDBACK_ROUNDTRIP_GREEN count=2 no_control=true');
console.log('D12_BAD_INPUT_REJECT_GREEN duplicate=1 control=1 quality=1');
console.log('D12_OFFLINE_NO_ROS_GAZEBO_REQUIRED');
