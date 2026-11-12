// 戴好页检查结果的文案：≥3 路过线说整条重贴并露出服务端提醒，1–2 路才点名往哪侧压一格。
import assert from 'node:assert/strict';
import { wearVerdict, WHOLE_BAND_BAD } from './src/emg8/placement.ts';
const warn = ['工频 3.2 mV 偏大：离开插线板 / 充电器，触点补水', 'Mac 接着充电器：厂商要求用电池，拔掉充电器、扩展坞和外接显示器'];
const all = wearVerdict([1, 2, 3, 4, 5, 6, 7, 8], warn);
assert.equal(all.headline, '8 路都偏高');
assert.match(all.sub, /整条/); assert.doesNotMatch(all.sub, /CH1/, '0/8 不能再点名 CH1');
assert.deepEqual(all.warnings, warn, '8 路全过线要露出服务端提醒');
const three = wearVerdict([2, 5, 7], warn);
assert.equal(three.headline, '5 路贴好了，CH2、CH5、CH7 都偏高'); assert.deepEqual(three.warnings, warn);
const two = wearVerdict([3, 6], warn);
assert.equal(two.headline, '6 路贴好了，CH3、CH6 还差一点');
assert.equal(two.sub, '把表带往 CH3 那侧压一格，再检查一次'); assert.deepEqual(two.warnings, [], '1–2 路照旧不露提醒');
const none = wearVerdict([], warn);
assert.equal(none.headline, '8 路都贴好了'); assert.deepEqual(none.warnings, warn);
assert.equal(wearVerdict([], []).sub, '可以开始录动作');
assert.equal(WHOLE_BAND_BAD, 3);
console.log('check-wear-hint ok');
