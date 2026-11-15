// T0-c：独立正式包 OpenEMG.app 端到端真窗口验证 + 16/8/2ch 切档 + 必败反例（record=false / 回放禁录）+ 实拍截图
// 绝不触碰 /Applications/OpenEMG.app 或用户真实数据目录。
const { app, BrowserWindow } = require('electron');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..', '..');
const ARTIFACT_DIR = process.env.OPENEMG_E2E_OUT || os.tmpdir();
const SIM_DIR = ARTIFACT_DIR;
const PACKAGED_APP = process.env.OPENEMG_APP_PATH || path.join(REPO_ROOT, 'app', 'out', 'OpenEMG-darwin-arm64', 'OpenEMG.app');
const PACKAGED_RES = path.join(PACKAGED_APP, 'Contents', 'Resources');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'yuanli-t0c-e2e-'));
process.env.YUANLI_USERDATA = tmpRoot;
// 不设进程级 YUANLI_DEVICE，防止与 main.tsx 首次挂载默认 wl8 抢杀 collector；走真实顶栏下拉框切换
delete process.env.YUANLI_DEVICE;
process.env.YUANLI_PY = path.join(PACKAGED_RES, 'python', 'bin', 'python3');
process.env.YUANLI_HOST = path.join(PACKAGED_RES, 'host');

const buildInfo = JSON.parse(fs.readFileSync(path.join(PACKAGED_RES, 'build-info.json'), 'utf8'));
if (!buildInfo.commit || !fs.existsSync(process.env.YUANLI_PY)) {
  console.error('T0C_FAIL 缺少正式包 Resources:', buildInfo);
  process.exit(1);
}

require(path.join(PACKAGED_RES, 'app', 'electron', 'main.cjs'));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitFor(win, jsExpr, timeoutMs = 35000, label = jsExpr) {
  const t0 = Date.now();
  let lastErr = '';
  while (Date.now() - t0 < timeoutMs) {
    try {
      const val = await win.webContents.executeJavaScript(jsExpr);
      if (val) return val;
    } catch (e) {
      lastErr = String(e);
    }
    await sleep(250);
  }
  const snap = await win.webContents.executeJavaScript(`document.body.innerText.slice(0, 600)`).catch(() => '');
  throw new Error(`等待超时 (${label}) lastErr=${lastErr} body=${JSON.stringify(snap)}`);
}

async function selectDeviceInUI(win, tier) {
  return await win.webContents.executeJavaScript(`(() => {
    const sel = document.querySelector('select.yuanli-device-select');
    if (!sel) return false;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
    setter.call(sel, ${JSON.stringify(tier)});
    sel.dispatchEvent(new Event('change', { bubbles: true }));
    return sel.value === ${JSON.stringify(tier)};
  })()`);
}

app.whenReady().then(async () => {
  const report = {
    commit: buildInfo.commit,
    packaged_app: PACKAGED_APP,
    userdata: tmpRoot,
    checks: {},
    screenshots: [],
  };
  try {
    let win = null;
    const t0 = Date.now();
    while (!win && Date.now() - t0 < 10000) {
      win = BrowserWindow.getAllWindows()[0] || null;
      if (!win) await sleep(100);
    }
    if (!win) throw new Error('主窗口未创建');
    win.setSize(1440, 920);

    // 等待页面挂载出顶栏设备下拉框（含全部 5 档）
    const options = await waitFor(
      win,
      `(() => {
        const sel = document.querySelector('select.yuanli-device-select');
        if (!sel || sel.options.length < 5) return null;
        return [...sel.options].map(o => ({ value: o.value, label: o.textContent }));
      })()`,
      15000,
      '顶栏 5 档设备下拉框挂载'
    );
    report.checks.device_dropdown_options = options;

    // 1. 在 UI 顶栏真实切换到「16 通道 · OpenEMG 双 ADS1298」(c08b-16ch)
    await sleep(400);
    const picked16 = await selectDeviceInUI(win, 'c08b-16ch');
    if (!picked16) throw new Error('未能选中 c08b-16ch');

    const onlineInfo = await waitFor(
      win,
      `(() => {
        const text = document.body.innerText || '';
        if (text.includes('16 / 16') && (text.includes('OpenEMG 16 路合成预览就绪') || text.includes('手环醒了'))) {
          return {
            headline: text.includes('OpenEMG 16 路合成预览就绪') ? 'OpenEMG 16 路合成预览就绪' : '手环醒了',
            spec: '16 / 16',
            has_synth_banner: text.includes('C08B-SYNTH') && text.includes('这不是现场数据'),
          };
        }
        return null;
      })()`,
      45000,
      'c08b-16ch 16/16 在线'
    );
    if (!onlineInfo.has_synth_banner) throw new Error('缺少 C08B-SYNTH 非现场数据安全横幅');
    report.checks.c08b_16ch_connect = onlineInfo;

    // 2. 切到「录动作」页让 16 路满高滚动波形 + 16 路电极环跑满 1.8 秒后截图 #1
    await win.webContents.executeJavaScript(`(() => {
      const capBtn = [...document.querySelectorAll('button')].find(b => (b.textContent || '').includes('录动作'));
      if (capBtn) capBtn.click();
      return !!capBtn;
    })()`);
    await waitFor(
      win,
      `(() => {
        const items = document.querySelectorAll('.emg8-ch-readout li:not(.note)');
        const txt = document.body.innerText || '';
        return items.length === 16 && txt.includes('16 CH · 1000 Hz') && txt.includes('µV') ? items.length : 0;
      })()`,
      15000,
      '16路实时波形与读数渲染'
    );
    await sleep(1800);
    const shotWave = path.join(ARTIFACT_DIR, 't0c_openemg_16ch_waveform.png');
    fs.writeFileSync(shotWave, (await win.webContents.capturePage()).toPNG());
    report.screenshots.push(shotWave);

    // 3. 必败反例 #1：c08b-16ch 默认 capabilities.record=false，请求 sessionStart 与旧采集页 record 都必须被拒绝
    const recReject16 = await win.webContents.executeJavaScript(`(async () => {
      const pid = window.pt.projectId;
      const s1 = await window.pt.emg8.studio(pid, 'sessionStart', { subject: 'S01', donning: 1, hand: 'left', placement: 'test' });
      const s2 = await window.pt.emg8.record(pid, { label: 'rest', seconds: 1, hand: 'left', donning: 1 });
      return { studio_sessionStart: s1, legacy_record: s2 };
    })()`);
    if (recReject16.studio_sessionStart.ok || recReject16.legacy_record.ok) {
      throw new Error('必败反例失效：c08b-16ch (record=false) 居然放行了录制！' + JSON.stringify(recReject16));
    }
    report.checks.negative_c08b16_record_locked = recReject16;

    // 4. 切到「数据台」→「设备」子页 → 点「示例 16CH」解码首板十项自检 + 展示 16 路连接器脚位表后截图 #2
    await win.webContents.executeJavaScript(`(() => {
      const btn = [...document.querySelectorAll('button')].find(b => (b.textContent || '').trim() === '数据台' || (b.textContent || '').includes('数据台'));
      if (btn) btn.click();
      return !!btn;
    })()`);
    await sleep(500);
    await win.webContents.executeJavaScript(`(() => {
      const devBtn = [...document.querySelectorAll('nav[aria-label="数据台页面"] button')].find(b => (b.textContent || '').trim() === '设备');
      if (devBtn) devBtn.click();
      return !!devBtn;
    })()`);
    await waitFor(
      win,
      `(() => (document.body.innerText || '').includes('默认锁定（record=false') && (document.body.innerText || '').includes('硬件通道与座子脚位对线表'))()`,
      12000,
      '数据台设备页安全锁与脚位表'
    );
    await win.webContents.executeJavaScript(`(() => {
      const sampleBtn = [...document.querySelectorAll('button')].find(b => (b.textContent || '').trim() === '示例 16CH');
      if (sampleBtn) sampleBtn.click();
      return !!sampleBtn;
    })()`);
    await waitFor(
      win,
      `(() => (document.body.innerText || '').includes('PASS') && (document.body.innerText || '').includes('0x03FF'))()`,
      8000,
      'c08b-bringup 示例 16CH 十项自检 PASS'
    );
    await sleep(400);
    const shotBench = path.join(ARTIFACT_DIR, 't0c_openemg_16ch_workbench.png');
    fs.writeFileSync(shotBench, (await win.webContents.capturePage()).toPNG());
    report.screenshots.push(shotBench);

    // 5. 在 UI 顶栏依次切到 c08b-8ch 与 c08b-2ch，验证采集服务自动热重启到 8 路与 2 路且安全锁保持关闭
    for (const [tier, expCh] of [['c08b-8ch', 8], ['c08b-2ch', 2]]) {
      const okSel = await selectDeviceInUI(win, tier);
      if (!okSel) throw new Error(`UI 选中 ${tier} 失败`);
      const stTier = await waitFor(
        win,
        `(async () => {
          const r = await window.pt.emg8.state();
          if (r.ok && r.value?.rig?.n_channels === ${expCh} && r.value?.rig?.streaming) {
            const d = await window.pt.emg8.studio(window.pt.projectId, 'deviceState');
            if (d.ok && d.value?.device_id === ${JSON.stringify(tier)}) {
              return {
                device_id: d.value.device_id,
                n_channels: d.value.n_channels,
                fs_Hz: d.value.fs_Hz,
                record: d.value.capabilities.record,
                banner: r.value.rig.banner,
              };
            }
          }
          return null;
        })()`,
        30000,
        `切换到 ${tier}`
      );
      if (stTier.record !== false) throw new Error(`${tier} 安全锁异常: ${JSON.stringify(stTier)}`);
      report.checks[tier] = stTier;
    }

    const outReport = path.join(SIM_DIR, 't0c_packaged_e2e_report.json');
    fs.writeFileSync(outReport, JSON.stringify(report, null, 2) + '\n');
    console.log('T0C_PACKAGED_E2E_PASS', JSON.stringify(report));
    win.close();
    setTimeout(() => {
      fs.rmSync(tmpRoot, { recursive: true, force: true });
      app.exit(0);
    }, 300);
  } catch (err) {
    console.error('T0C_PACKAGED_E2E_FAIL', err);
    try { fs.rmSync(tmpRoot, { recursive: true, force: true }); } catch {}
    app.exit(1);
  }
});
