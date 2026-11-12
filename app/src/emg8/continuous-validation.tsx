import { useEffect, useRef, useState } from 'react';
import type { Emg8Bridge } from './contract';
import { LABEL_CN } from './contract';
import { validationPlan } from './validation-plan';

type Log = (kind: string, data?: Record<string, unknown>) => void;
type Props = { bridge: Emg8Bridge; projectId: string; ready: boolean; donning: number; labels: string[]; onBusy: (v: boolean) => void; logger: { current: Log | null } };
export function ContinuousValidation({ bridge, projectId, ready, donning, labels, onBusy, logger }: Props) {
  const [busy, setBusy] = useState(false), [text, setText] = useState('连续验证 · 同步手部视频'), [error, setError] = useState('');
  const [remaining, setRemaining] = useState(0), [saved, setSaved] = useState('');
  const video = useRef<HTMLVideoElement>(null), canvas = useRef<HTMLCanvasElement>(null);
  const stopRef = useRef<(reason: string) => Promise<void>>(async () => {});
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; void stopRef.current('离开验证页面'); }; }, []);
  useEffect(() => { if (!ready && busy) void stopRef.current('识别或连接已停止'); }, [ready, busy]);
  const [cameras, setCameras] = useState<MediaDeviceInfo[]>([]), [cameraId, setCameraId] = useState('');
  const [opening, setOpening] = useState(false), [previewReady, setPreviewReady] = useState(false), [confirmed, setConfirmed] = useState(false);
  const previewStream = useRef<MediaStream | null>(null), previewEpoch = useRef(0), recording = useRef(false);
  const chosenCamera = useRef(''), manualCamera = useRef(false);
  const closePreview = () => {
    previewEpoch.current++;
    previewStream.current?.getTracks().forEach(t => t.stop()); previewStream.current = null;
    if (!recording.current && video.current) video.current.srcObject = null;
    if (alive.current) { setOpening(false); setPreviewReady(false); setConfirmed(false); }
    if (!recording.current) onBusy(false);
  };
  const listCameras = async () => {
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === 'videoinput');
    if (alive.current) {
      setCameras(devices);
      if (!chosenCamera.current) {
        const preferred = devices.find(d => /osmo.*action\s*5|action\s*5/i.test(d.label)) ?? devices[0];
        chosenCamera.current = preferred?.deviceId ?? ''; setCameraId(chosenCamera.current);
      }
    }
    return devices;
  };
  useEffect(() => {
    const refresh = () => { void listCameras().catch(e => { if (alive.current) setError('无法读取摄像头列表：' + String(e)); }); };
    refresh(); navigator.mediaDevices.addEventListener('devicechange', refresh);
    return () => { navigator.mediaDevices.removeEventListener('devicechange', refresh); closePreview(); };
  }, []);
  const openPreview = async (id = chosenCamera.current) => {
    if (recording.current) return;
    closePreview(); const epoch = previewEpoch.current;
    setOpening(true); setError(''); setSaved(''); setText('正在打开摄像头预览，不会开始录制');
    let stream: MediaStream | null = null;
    const current = () => alive.current && epoch === previewEpoch.current;
    const acquire = (deviceId: string) => navigator.mediaDevices.getUserMedia({ audio: false,
      video: { ...(deviceId ? { deviceId: { exact: deviceId } } : {}), width: 640, height: 480, frameRate: 30 } });
    try {
      stream = await acquire(id);
      if (!current()) return;
      // 首次授权前设备名可能为空；授权后重新枚举，优先Action 5，手动选过则不覆盖。
      const devices = await listCameras(); if (!current()) return;
      const action = !manualCamera.current && devices.find(d => /osmo.*action\s*5|action\s*5/i.test(d.label));
      if (action && action.deviceId !== stream.getVideoTracks()[0]?.getSettings().deviceId) {
        stream.getTracks().forEach(t => t.stop()); stream = await acquire(action.deviceId); id = action.deviceId;
      }
      if (!current()) return;
      const track = stream.getVideoTracks()[0];
      if (!track || track.readyState !== 'live' || (id && track.getSettings().deviceId !== id)) throw Error('所选摄像头不可用，请重新选择');
      chosenCamera.current = track.getSettings().deviceId || id; setCameraId(chosenCamera.current);
      previewStream.current = stream;
      track.onended = () => { if (current()) { closePreview(); setError('摄像头已断开，请重新选择并预览'); } };
      const v = video.current!; v.srcObject = stream; await v.play();
      if (!current()) return;
      // 见到首个画面才允许确认，不能把授权成功当作已有可用视频。
      await new Promise<void>((resolve, reject) => {
        let frame = 0;
        const timeout = setTimeout(() => { if (frame) v.cancelVideoFrameCallback(frame); reject(Error('摄像头没有传来画面')); }, 5000);
        frame = v.requestVideoFrameCallback(() => { clearTimeout(timeout); resolve(); });
      });
      if (!current()) return;
      setOpening(false); setPreviewReady(true); setText('预览中 · 调整镜头，让手和手指完整入镜');
      stream = null; // 预览引用持有它，录制直接复用，不重新打开默认摄像头。
    } catch (e) {
      if (current()) { closePreview(); setError('摄像头预览失败：' + String(e)); setText('请选择摄像头后重新预览'); }
    } finally { stream?.getTracks().forEach(t => t.stop()); }
  };
  const start = async () => {
    if (recording.current || !ready || !previewReady || !confirmed || !previewStream.current || !bridge.validation) return;
    recording.current = true;
    setBusy(true); onBusy(true); setError(''); setSaved(''); setRemaining(0); setText('正在启动录制，尚未倒计时');
    let sid = '', stream: MediaStream | null = previewStream.current, recorded: MediaStream | null = null, recorder: MediaRecorder | null = null;
    previewStream.current = null; previewEpoch.current++; setPreviewReady(false); setConfirmed(false);
    let stopping = false, videoOK = true, videoChunks = 0, eventId = 0, frameId = 0, timer = 0;
    let chain = Promise.resolve(), pending = 0, lastFrameMs = 0, acceptVideo = true;
    let bootResolve: () => void = () => {};
    const bootDone = new Promise<void>(resolve => { bootResolve = resolve; });
    const syncTasks = new Set<Promise<Awaited<ReturnType<typeof api>>>>();
    const events: Record<string, unknown>[] = [];
    const api = async (a: Record<string, unknown>) => {
      const r = await bridge.validation!(projectId, { ...a, ...(sid ? { id: sid } : {}) });
      if (!r.ok) throw Error(r.message); return r.value;
    };
    const fail = (e: unknown) => { videoOK = false; if (alive.current) setError(String(e)); void stopRef.current('录制或保存失败'); };
    const queue = (fn: () => Promise<unknown>) => {
      pending++;
      chain = chain.then(fn).then(() => { pending--; }).catch(e => { pending--; fail(e); });
      if (pending > 20) fail('保存速度跟不上，已停止以免丢视频');
    };
    const log: Log = (kind, data = {}) => { events.push({ ...data, kind, event_id: eventId++, client_ms: performance.now() }); };
    const flush = () => { if (events.length) { const batch = events.splice(0); queue(() => api({ action: 'events', events: batch })); } };
    const sync = () => {
      const task = (async () => {
      const send = performance.now(), r = await api({ action: 'clock' }), receive = performance.now();
      log('sync', { send_ms: send, receive_ms: receive, host_ms: r.host_ms, rtt_ms: receive - send });
      return r;
      })();
      syncTasks.add(task); void task.then(() => syncTasks.delete(task), () => syncTasks.delete(task));
      return task;
    };
    let stoppedResolve: (() => void) | null = null;
    const stopped = new Promise<void>(resolve => { stoppedResolve = resolve; });
    stopRef.current = async reason => {
      if (stopping) return;
      stopping = true; clearInterval(timer); logger.current = null;
      // 准备/时钟请求也可能尚未返回；从按停止起就保活，取得sid后自动生效。
      const savingHeartbeat = window.setInterval(() => { if (sid) void api({ action: 'clock' }).catch(() => { videoOK = false; }); }, 1000);
      if (alive.current) setText('正在保存，请稍等');
      try {
        // 停止必须等准备阶段和在途同步结束，避免收尾后又启动录像或遗失最后锚点。
        await bootDone;
        await Promise.allSettled([...syncTasks]);
        if (sid) { try { await api({ action: 'stop', reason }); } catch (e) { videoOK = false; if (alive.current) setError('原始录制停止失败：' + String(e)); } }
        try {
          if (recorder && recorder.state !== 'inactive') { recorder.stop(); await Promise.race([stopped, new Promise<void>((_, reject) => setTimeout(() => reject(Error('视频收尾超时，数据不完整')), 5000))]); }
        } catch (e) { videoOK = false; if (alive.current) setError(String(e)); }
        // 超时也收尾为不完整；迟到分片不能写进已结束会话。
        acceptVideo = false;
        if (video.current && frameId) video.current.cancelVideoFrameCallback(frameId);
        if (sid) { log('video_stop', { reason }); flush(); await chain; }
        if (sid) {
          const r = await api({ action: 'finish', video_chunks: videoChunks, video_ok: videoOK });
          if (alive.current) { setSaved(r.path); setText(r.complete ? '已保存，等待核对视频中的动作起止' : '已保存部分数据，本段不完整'); }
        } else if (alive.current) setText('尚未开始录制');
      } catch (e) { if (alive.current) setError('保存未完成：' + String(e)); }
      finally {
        clearInterval(savingHeartbeat);
        stream?.getTracks().forEach(t => t.stop()); recorded?.getTracks().forEach(t => t.stop());
        if (video.current) video.current.srcObject = null;
        recording.current = false; onBusy(false); if (alive.current) { setBusy(false); setRemaining(0); }
      }
    };
    try {
      // 复用用户已经确认的镜头；此处才启动原始录制与MediaRecorder。
      if (!stream || stream.getVideoTracks()[0]?.readyState !== 'live') throw Error('预览摄像头已断开，请重新预览');
      const v = video.current!, c = canvas.current!;
      stream.getVideoTracks()[0].onended = () => { videoOK = false; void stopRef.current('摄像头已停止'); };
      if (!v.requestVideoFrameCallback) throw Error('当前环境不支持视频帧时间记录');
      c.width = v.videoWidth || 640; c.height = v.videoHeight || 480;
      const ctx = c.getContext('2d')!;
      const created = await api({ action: 'start', donning, video_consent: true }); sid = created.id;
      if (stopping) return;
      logger.current = log;
      for (let i = 0; i < 3; i++) { await sync(); if (stopping) return; }
      const frame = (now: number, meta: VideoFrameCallbackMetadata) => {
        if (stopping) return;
        lastFrameMs = performance.now();
        ctx.drawImage(v, 0, 0, c.width, c.height);
        // 把对应单调时钟直接写进录像；后续逐帧标注不依赖WebM文件创建时间。
        ctx.fillStyle = '#000'; ctx.fillRect(0, c.height - 30, c.width, 30); ctx.fillStyle = '#fff'; ctx.font = '16px monospace';
        ctx.fillText(`T=${now.toFixed(3)} ms  frame=${meta.presentedFrames}`, 8, c.height - 9);
        log('video_frame', { frame_ms: now, media_time: meta.mediaTime, presented_frames: meta.presentedFrames,
          expected_display_ms: meta.expectedDisplayTime, capture_ms: (meta as VideoFrameCallbackMetadata & { captureTime?: number }).captureTime ?? null });
        frameId = v.requestVideoFrameCallback(frame);
      };
      frameId = v.requestVideoFrameCallback(frame);
      recorded = c.captureStream(30);
      const mime = ['video/webm;codecs=vp8', 'video/webm'].find(m => MediaRecorder.isTypeSupported(m));
      if (!mime) throw Error('当前环境不支持本机WebM录像');
      recorder = new MediaRecorder(recorded, { mimeType: mime, videoBitsPerSecond: 1200000 });
      recorder.ondataavailable = e => {
        if (!acceptVideo || !e.data.size) return;
        const index = videoChunks++;
        queue(async () => api({ action: 'video', index, bytes: new Uint8Array(await e.data.arrayBuffer()) }));
      };
      recorder.onstop = () => stoppedResolve?.();
      recorder.onerror = () => fail('视频录制出错');
      stream.getVideoTracks()[0].onended = () => { videoOK = false; void stopRef.current('摄像头已停止'); };
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => reject(Error('视频启动超时')), 5000);
        recorder!.onstart = () => { clearTimeout(timeout); lastFrameMs = performance.now(); log('video_start', { mime, camera_label: stream?.getVideoTracks()[0]?.label ?? '', width: c.width, height: c.height }); resolve(); };
        recorder!.start(1000);
      });
      if (stopping) return;
      const plan = validationPlan(labels, LABEL_CN), begun = performance.now();
      const total = plan.reduce((sum, p) => sum + p.seconds, 0); let lastCue = -1, lastSync = begun, syncing = false;
      const tick = () => {
        if (stopping) return;
        if (performance.now() - lastFrameMs > 1000) { log('capture_error', { reason: '摄像头超过一秒没有新帧' }); fail('摄像头停帧，本段已停止'); return; }
        const elapsed = (performance.now() - begun) / 1000;
        if (elapsed >= total) { void stopRef.current('计划完成'); return; }
        let end = 0, i = 0;
        for (; i < plan.length; i++) { end += plan[i].seconds; if (elapsed < end) break; }
        if (i !== lastCue) { lastCue = i; log('cue', { label: plan[i].label, text: plan[i].text, index: i, planned_seconds: plan[i].seconds }); if (alive.current) setText(plan[i].text); }
        if (alive.current) setRemaining(Math.ceil(total - elapsed));
        if (performance.now() - lastSync >= 1000 && !syncing) {
          lastSync = performance.now(); syncing = true; flush();
          void sync().then(r => { if (!r.active) void stopRef.current(r.reason || '原始录制已停止'); }).catch(fail).finally(() => { syncing = false; });
        }
      };
      timer = window.setInterval(tick, 100); tick();
    } catch (e) { fail(e); } finally { bootResolve(); }
  };
  return <section className="emg8-card" style={{ marginTop: 16 }}>
    <div className="emg8-live-head"><h3>连续验证 · 仅存本机</h3><span>{busy ? (remaining > 0 ? `剩余约 ${remaining} 秒` : '准备或保存中') : '开始录制后约 4 分钟'}</span></div>
    <h2 role="status">{text}</h2>
    <p>放松 → 随机做三类手势 → 随意动手。手和手指完整入镜，不用拍脸。录制时只记触发，不发送游戏。</p>
    <fieldset disabled={busy} style={{ border: 0, padding: 0, marginBottom: 12 }}>
      <label>摄像头 <select aria-label="连续验证摄像头" value={cameraId} onChange={e => {
        const id = e.target.value; manualCamera.current = true; chosenCamera.current = id; setCameraId(id);
        if (previewReady || opening) void openPreview(id); else setConfirmed(false);
      }}>
        <option value="">选择摄像头</option>
        {cameras.map((d, i) => <option key={d.deviceId || i} value={d.deviceId}>{d.label || `摄像头 ${i + 1}（预览授权后显示名称）`}</option>)}
      </select></label>{' '}
      <button disabled={opening} onClick={() => void openPreview()}>开启预览</button>{' '}
      {(opening || previewReady) && <button onClick={() => { closePreview(); setText('预览已关闭，尚未录制'); }}>关闭预览</button>}
    </fieldset>
    {!busy && <p className="emg8-fine">优先选择 Action 5；预览不保存、不倒计时。切换镜头后需重新确认手部入镜。</p>}
    {!ready && !busy && <p className="emg8-fine">可以先预览；手环连接并开始识别后，才能开始录制。</p>}
    <video ref={video} muted playsInline style={{ display: busy || opening || previewReady ? 'block' : 'none', width: '100%', maxWidth: 480, borderRadius: 8 }} />
    <canvas ref={canvas} style={{ display: 'none' }} />
    {error && <p className="emg8-warn" role="alert">{error}</p>}
    {saved && <p className="emg8-fine">保存位置：{saved}<br />视频起止还未标注，暂不生成延迟或误触成绩。</p>}
    {!busy && <p><label><input type="checkbox" checked={confirmed} disabled={!previewReady} onChange={e => setConfirmed(e.target.checked)} /> 手和手指已完整入镜</label></p>}
    <button className={busy ? 'emg8-stop' : 'emg8-primary'} disabled={!busy && (!ready || !previewReady || !confirmed || !bridge.validation)} onClick={() => busy ? void stopRef.current('用户停止') : void start()}>{busy ? '停止并保存已有部分' : '开始录制与倒计时'}</button>
    <p className="emg8-fine">只录手部视频，不录声音；原始肌电和视频都不上传、不加入训练。断流会结束本段并保留已有部分。录像时间精度需核对帧率与同步误差。</p>
  </section>;
}
