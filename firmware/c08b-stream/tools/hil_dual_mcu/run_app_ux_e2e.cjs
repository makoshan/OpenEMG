// App 体验优化真窗口端到端验证：
// 1) userData/device.json 持久化冷启动零双启（window.pt.initialDevice 同步注入，仅 1 个 Python 采集子进程）
// 2) C08B 连接页隐藏唯理专属「USB 版/蓝牙版」开关，显示 C08B 链路与硬件锁状态条 + 一键跳「首板自检与脚位表 →」
// 3) C08B 佩戴页展示 16/8/2ch 专属电极排布（大—辅—大）与 USB VBUS 互锁提醒；切回 wl8 时完整恢复唯理「USB 版/蓝牙版」
// 4) 数据台「设备」子页默认折叠 16 行通道名，1440×920 首屏同时露出安全锁、首板自检解码（含 97B 16 路 µVpp/µVrms 详报）与连接器脚位表（含实时检索）
const { app, BrowserWindow } = require('electron');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..', '..');
const ARTIFACT_DIR = process.env.OPENEMG_E2E_OUT || os.tmpdir();
const SIM_DIR = ARTIFACT_DIR;
const PACKAGED_APP = process.env.OPENEMG_APP_PATH || path.join(REPO_ROOT, 'app', 'out', 'OpenEMG-darwin-arm64', 'OpenEMG.app');
const PACKAGED_RES = path.join(PACKAGED_APP, 'Contents', 'Resources');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'yuanli-ux-e2e-'));
// 预写入上次选择的档位 c08b-16ch，验证冷启动直接以 c08b-16ch 挂载、不先起 wl8 再杀掉重起
fs.writeFileSync(path.join(tmpRoot, 'device.json'), JSON.stringify({ device: 'c08b-16ch' }) + '\n');

process.env.YUANLI_USERDATA = tmpRoot;
delete process.env.YUANLI_DEVICE;
process.env.YUANLI_PY = path.join(PACKAGED_RES, 'python', 'bin', 'python3');
process.env.YUANLI_HOST = path.join(PACKAGED_RES, 'host');

const buildInfo = JSON.parse(fs.readFileSync(path.join(PACKAGED_RES, 'build-info.json'), 'utf8'));
if (!buildInfo.commit || !fs.existsSync(process.env.YUANLI_PY)) {
  console.error('UX_E2E_FAIL 缺少正式包 Resources:', buildInfo);
  process.exit(1);
}

require(path.join(PACKAGED_RES, 'app', 'electron', 'main.cjs'));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function countCollectorProcs() {
  const out = execFileSync('/bin/ps', ['-ax', '-o', 'pid=,command='], { encoding: 'utf8' });
  return out
    .split('\n')
    .filter((l) => l.includes('emg8-server.py') && l.includes(tmpRoot));
}

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
    await sleep(220);
  }
  const snap = await win.webContents.executeJavaScript(`document.body.innerText.slice(0, 700)`).catch(() => '');
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

    // 1. 冷启动持久化单进程验证：直接就是 c08b-16ch，且全系统只有 1 个归属本 userData 的 emg8-server.py
    const coldBoot = await waitFor(
      win,
      `(() => {
        const sel = document.querySelector('select.yuanli-device-select');
        const txt = document.body.innerText || '';
        if (!sel || !txt.includes('16 / 16') || !(txt.includes('OpenEMG 16 路合成预览就绪') || txt.includes('手环醒了'))) return null;
        return {
          initialDevice: window.pt?.initialDevice?.device ?? window.pt?.initialDevice,
          selectedValue: sel.value,
          weiliKindSwitchCount: document.querySelectorAll('[aria-label="手环接法"]').length,
          hasC08bStrip: !!document.querySelector('.emg8-c08b-strip'),
          c08bStripText: document.querySelector('.emg8-c08b-strip')?.innerText || '',
          hasSynthBanner: txt.includes('C08B-SYNTH') && txt.includes('这不是现场数据'),
        };
      })()`,
      35000,
      '冷启动直接进入 c08b-16ch 在线态'
    );
    const procs = countCollectorProcs();
    if (coldBoot.initialDevice !== 'c08b-16ch' || coldBoot.selectedValue !== 'c08b-16ch') {
      throw new Error('冷启动 initialDevice 未对齐 c08b-16ch: ' + JSON.stringify(coldBoot));
    }
    if (procs.length !== 1 || !procs[0].includes('--device c08b-16ch')) {
      throw new Error('冷启动采集进程数量或参数异常: ' + JSON.stringify(procs));
    }
    if (coldBoot.weiliKindSwitchCount !== 0 || !coldBoot.hasC08bStrip) {
      throw new Error('C08B 连接页未隐藏唯理开关或缺少 C08B 状态条: ' + JSON.stringify(coldBoot));
    }
    report.checks.cold_start_single_spawn = { ...coldBoot, collector_procs: procs.length, collector_cmd_has_c08b16: true };

    await sleep(400);
    const shotSetup = path.join(ARTIFACT_DIR, 'app_ux_c08b_setup.png');
    fs.writeFileSync(shotSetup, (await win.webContents.capturePage()).toPNG());
    report.screenshots.push(shotSetup);

    // 2. 点「去戴好它 →」进入佩戴页，核对 C08B 16ch 专属佩戴提示（大—辅—大 + USB 互锁提醒，无唯理丝印文案）
    await win.webContents.executeJavaScript(`(() => {
      const btn = [...document.querySelectorAll('button')].find(b => (b.textContent || '').includes('去戴好它') || (b.textContent || '').includes('戴好'));
      if (btn) btn.click();
      return !!btn;
    })()`);
    const wearInfo = await waitFor(
      win,
      `(() => {
        const txt = document.body.innerText || '';
        if (!txt.includes('大—辅—大')) return null;
        return {
          has_12_2_2: txt.includes('大—辅—大'),
          has_vbus_note: txt.includes('USB'),
          has_weili_silk: txt.includes('唯理丝印'),
        };
      })()`,
      10000,
      'C08B 16ch 专属佩戴步骤'
    );
    if (wearInfo.has_weili_silk) throw new Error('C08B 佩戴页混入唯理丝印文案');
    report.checks.c08b_wear_steps = wearInfo;

    // 3. 回到第 1 步「连上」，点「首板自检与脚位表 →」一键直达「数据台 -> 设备」
    await win.webContents.executeJavaScript(`(() => {
      const step1 = [...document.querySelectorAll('.ins-stepbar button, button')].find(b => (b.textContent || '').includes('连上'));
      if (step1) step1.click();
      return !!step1;
    })()`);
    await sleep(250);
    const jumped = await win.webContents.executeJavaScript(`(() => {
      const jumpBtn = [...document.querySelectorAll('.emg8-c08b-strip button')].find(b => (b.textContent || '').includes('首板自检与脚位表'));
      if (jumpBtn) jumpBtn.click();
      return !!jumpBtn;
    })()`);
    if (!jumped) throw new Error('未找到「首板自检与脚位表 →」按钮');

    // 验证首屏三张核心硬件卡在 1440×920 视口全部位于首屏可见区（top < 860），且 16 行通道名默认折叠
    const firstScreenLayout = await waitFor(
      win,
      `(() => {
        const cards = [...document.querySelectorAll('.emg8-card')];
        const lockCard = cards.find(c => c.innerText.includes('设备与安全门锁'));
        const bringupCard = cards.find(c => c.innerText.includes('首板上电自检解码'));
        const pinCard = cards.find(c => c.innerText.includes('硬件通道与座子脚位对线表'));
        const chWrap = document.querySelector('.emg8-ch-collapse');
        const chGrid = document.querySelector('.emg8-ch-grid');
        if (!lockCard || !bringupCard || !pinCard || !chWrap) return null;
        return {
          viewportHeight: window.innerHeight,
          chEditorCollapsedByDefault: !chGrid && chWrap.innerText.includes('展开改名'),
          lockCardTop: Math.round(lockCard.getBoundingClientRect().top),
          bringupCardTop: Math.round(bringupCard.getBoundingClientRect().top),
          pinCardTop: Math.round(pinCard.getBoundingClientRect().top),
        };
      })()`,
      12000,
      '数据台设备页首屏三卡同屏检查'
    );
    if (
      !firstScreenLayout.chEditorCollapsedByDefault ||
      firstScreenLayout.lockCardTop >= 860 ||
      firstScreenLayout.bringupCardTop >= 860 ||
      firstScreenLayout.pinCardTop >= 860
    ) {
      throw new Error('首屏三卡未同屏露出: ' + JSON.stringify(firstScreenLayout));
    }
    report.checks.workbench_first_screen = firstScreenLayout;

    // 4. 点「示例 97B 详报」，核验 97B SWD 详报 16 路 µVpp / µVrms 网格 + 脚位表搜索过滤
    await win.webContents.executeJavaScript(`(() => {
      const b = [...document.querySelectorAll('button')].find(x => (x.textContent || '').includes('示例 97B 详报'));
      if (b) b.click();
      return !!b;
    })()`);
    const report97 = await waitFor(
      win,
      `(() => {
        const cells = document.querySelectorAll('.emg8-ch-cell');
        const meta = document.querySelector('.emg8-report97-meta')?.innerText || '';
        if (cells.length !== 16 || !meta.includes('500 Hz')) return null;
        return {
          cells: cells.length,
          meta,
          sampleCell0: cells[0].innerText,
          sampleCell15: cells[15].innerText,
        };
      })()`,
      10000,
      '97B 16路 µVpp/µVrms 详报渲染'
    );
    report.checks.bringup_97b_report = report97;

    // 测试脚位表实时筛选（输入 FPC3 -> 仅剩 FPC3 行；清空 -> 恢复全部 16 行）
    const filterCheck = await win.webContents.executeJavaScript(`(async () => {
      const inp = document.querySelector('input[aria-label="筛选通道或脚位"]');
      if (!inp) return null;
      const setVal = (v) => {
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(inp, v);
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      };
      const fullRows = inp.closest('.emg8-card').querySelectorAll('tbody tr').length;
      setVal('FPC3');
      await new Promise(r => setTimeout(r, 80));
      const fpc3Rows = inp.closest('.emg8-card').querySelectorAll('tbody tr').length;
      setVal('');
      await new Promise(r => setTimeout(r, 80));
      const restoredRows = inp.closest('.emg8-card').querySelectorAll('tbody tr').length;
      return { fullRows, fpc3Rows, restoredRows };
    })()`);
    if (!filterCheck || filterCheck.fullRows !== 16 || filterCheck.fpc3Rows >= 16 || filterCheck.fpc3Rows === 0 || filterCheck.restoredRows !== 16) {
      throw new Error('脚位表搜索过滤异常: ' + JSON.stringify(filterCheck));
    }
    report.checks.pinout_filter = filterCheck;

    await sleep(350);
    const shotBench97 = path.join(ARTIFACT_DIR, 'app_ux_c08b_workbench_97b.png');
    fs.writeFileSync(shotBench97, (await win.webContents.capturePage()).toPNG());
    report.screenshots.push(shotBench97);

    // 5. 切回商用唯理 8 通道 (wl8)，核验：
    //    a) userData/device.json 立即持久化为 wl8
    //    b) 回到引导「连接」步后，「USB 版 / 蓝牙版」开关完整恢复，C08B 状态条不出现
    const okWl8 = await selectDeviceInUI(win, 'wl8');
    if (!okWl8) throw new Error('切换 wl8 失败');
    await waitFor(
      win,
      `(async () => {
        const d = await window.pt.emg8.studio(window.pt.projectId, 'deviceState');
        return d.ok && d.value?.device_id === 'wl8' ? d.value : null;
      })()`,
      25000,
      '切换回 wl8'
    );
    const savedWl8 = JSON.parse(fs.readFileSync(path.join(tmpRoot, 'device.json'), 'utf8'));
    if (savedWl8.device !== 'wl8') throw new Error('device.json 未持久化 wl8: ' + JSON.stringify(savedWl8));

    // 点顶栏步骤条「连上」回连接页，验证唯理 USB/蓝牙版开关完好无损
    await win.webContents.executeJavaScript(`(() => {
      const step1 = [...document.querySelectorAll('.ins-stepbar button, button')].find(b => (b.textContent || '').includes('连上'));
      if (step1) step1.click();
      return !!step1;
    })()`);
    const wl8Setup = await waitFor(
      win,
      `(() => {
        const ks = document.querySelectorAll('[aria-label="手环接法"]');
        const strip = document.querySelectorAll('.emg8-c08b-strip');
        return ks.length === 1 && strip.length === 0
          ? { weiliKindSwitchCount: ks.length, c08bStripCount: strip.length, text: ks[0].innerText }
          : null;
      })()`,
      10000,
      'wl8 连接页恢复 USB 版 / 蓝牙版开关'
    );
    report.checks.wl8_regression_ok = { savedDeviceJson: savedWl8, wl8Setup };

    const outReport = path.join(SIM_DIR, 'app_ux_e2e_report.json');
    fs.writeFileSync(outReport, JSON.stringify(report, null, 2) + '\n');
    console.log('APP_UX_E2E_PASS', JSON.stringify(report));
    win.close();
    setTimeout(() => {
      fs.rmSync(tmpRoot, { recursive: true, force: true });
      app.exit(0);
    }, 300);
  } catch (err) {
    console.error('APP_UX_E2E_FAIL', err);
    try { fs.rmSync(tmpRoot, { recursive: true, force: true }); } catch {}
    app.exit(1);
  }
});
