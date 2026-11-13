import { PROFILES } from './profiles';
import type { RigLink } from './link';
// 八通道肌电工作室 ↔ 主进程（desktop/emg8-ipc.cjs）↔ 手表仓库采集服务（firmware/emg_web.py --wl8）的契约。
// 形状跟着服务端：wl8_ab.Recorder.state()、wl8_train.train() 的 run.json、LivePredictor.push()。改形状两端一起改。
import type { Result } from '../desktop-bridge';

export type Hand = 'left' | 'right';
export type Phase = 'prepare' | 'rest' | 'hold' | 'release' | 'daily';
export type AbProgress = {
  step: string; title: string; phase: Phase; text: string; force: 'light' | 'medium' | null; aim: boolean;
  cycle: number; cycles: number; phase_dur: number; phase_elapsed: number; step_remaining: number;
  completed: number; voided: number[]; cycle_plan: { phase: Phase; dur: number }[];
};
export type AbStep = { key: string; title: string; hint: string };
export type AbState = {
  protocol: string; active: boolean; paused: boolean; progress: Partial<AbProgress>; steps: AbStep[]; purposes: Record<string, string>;
  last_saved: { path: string; step: string; stopped: boolean; completed: number; voided: number[]; emg_samples: number; dropped: number } | null;
  done?: Record<string, { files: number; cycles: number; voided: number }>;
};
export type Conditions = {
  emg_samples: number; imu_samples: number; mains_mv?: number; noise_uv?: number; noise_per_channel?: number[];
  baseline_uv?: number[]; vpp_uv?: number[]; spectral_db?: number[];
  acc_g?: number; gyro_rad_s?: number; power?: 'battery' | 'ac' | 'unknown'; warnings: string[];
};
export type TrainEvent =
  | { stage: 'data'; message: string } | { stage: 'same_wear'; value: number }
  | { stage: 'rewear'; value: number; source?: Run['rewear_source']; shuffled: number; per_channel: number[] }
  | { stage: 'curve'; n: number; mean: number; std: number } | { stage: 'done'; rewear: number | null; same_wear: number };
export type Pred = {
  validation?: { id: string; window_start: number; window_end: number };
  probs: Record<string, number>; top: string; xy: [number, number]; t: number; stable?: string;
  signal?: { baseline_uv: number; vpp_uv: number; noise_db: number | null };
  gate?: { threshold_uv: number; sensitivity: number; effective_uv: number; blocked: boolean; min_prob?: number; unsure?: boolean; threshold_x?: number | null; rest_ref_uv?: number | null };   // threshold_x：幅度门槛按放松底噪的倍数；rest_ref_uv：模型记的放松底噪（没记是 null）   // unsure：最高类概率低于动作阈值，判回放松
  mask?: number[];   // 服务端当前屏蔽的路（1–8），这次识别没用它们的特征
};   // stable：前端防抖后的类别。signal / gate 由识别门槛附在每次预测上
export type Wl8State = {
  ab: AbState; train: { running?: boolean; events: TrainEvent[]; run_id?: string | null; error?: string | null; labels?: string[] };
  live: { run_id: string; last: Pred | null } | null; replay: string | null; cursor?: CursorState; ai?: AiRequest; ctrl?: CtrlState;
};
/** 控制串口（host/wl8_ctrl.py）：识别结果发给外设；log 新的在前，t 是 time.time() 秒 */
export type CtrlState = { port: string; baud: number; open: boolean; error: string; log: { t: number; code: number; label: string }[] };
/** 光标控制器（firmware/wl8_cursor.Controller.state()）。阶段一只移动，不点击 */
export type CursorMode = 'off' | 'calibrating' | 'log' | 'move' | 'drag';
export type CursorState = {
  mode: CursorMode; note: string; gain: number; deadzone: number; accel?: number; moves: number; v: [number, number];
  calib: { kind?: 'imu' | 'pinch'; t: number; total: number; step: number; text: string; plan: { start: number; dur: number; text: string; key: string }[] } | null;
  cal: { x_axis: number; x_sign: number; y_axis: number; y_sign: number; created: string } | null;
  drift: { max_px: number; done: boolean; left_s: number; wait_s?: number; peak_w?: number; moved?: boolean } | null;
  imu_age_ms: number | null; trusted: boolean | null; replay: boolean;
  pcal?: { channels: number[]; on: number; off: number; rest_p95: number; pinch_p25: number; move_p90: number | null; created: string } | null;
  score?: number; button?: CursorButton; emg_age_ms?: number | null; still?: boolean; artifacts?: number;
  events?: { down: number; up: number; paired: boolean; last: [number, 'down' | 'up', number][] };
  opts?: CursorOpts; clicks?: number; bias_shift?: number | null;
  /** 主机侧：IMU 块到达间隔（p50/p95/max ms，long = 超过 100 ms 的次数）、回调处理时间 p95 */
  update_ms?: { p50: number | null; p95: number | null; max: number | null; long: number; n: number; proc_p95: number | null };
};
/** 跟手与单击的开关（A1 自适应平滑、A3 软死区 / 零点修正、A2 短捏单击），可逐项对照 */
export type CursorOpts = { adaptive: boolean; soft: boolean; rezero: boolean; click: boolean };
/** 左键：松开 / 刚捏上还没满 0.3 秒 / 按下 */
export type CursorButton = 'up' | 'pending' | 'down';
/** AI 确认钩子当前这一次请求（原力手环 host/wl8_actions.AiPending；时间是 time.time() 秒） */
export type AiRequest = { state: 'idle' | 'pending' | 'done'; seq: number; cmd?: string; started?: number; deadline?: number; decision?: 'allow' | 'deny'; reason?: string; ms?: number | null; ended?: number };
export type CursorTick = { mode: CursorMode; vx: number; vy: number; score?: number; button?: CursorButton };
export type { RigLink };
export type ServiceState = {
  project: { id: string; name: string } | null;
  rig: { port: string | null; kind: string; banner: string; streaming: boolean; n_channels?: number; fs_Hz?: number; replay?: string; error?: string; link?: RigLink; link_detail?: string; link_since?: number | null /* 这一段连续出数据从什么时候开始（epoch 秒）；旧服务没有 */ };
  busy: string | null; progress: { label?: string; take?: number; count?: number; phase?: string };
  log: string[]; counts: Record<string, Record<string, Record<string, number>>>; tiers: string[]; wl8: Wl8State | null;
};
export type Point = { x: number; y: number; label: string };
export type Run = {
  id: string; created: string; labels: string[]; counts: { train: Record<string, number>; rewear: Record<string, number> };
  same_wear: number; rewear: number | null; rewear_source?: '重戴目录' | '留一次佩戴'; shuffled?: number; per_channel?: number[];
  confusion?: { rows: string[]; matrix: number[][] };
  learning_curve: { points: { n: number; mean: number; std: number }[]; tested_on: string };
  projection: { train: Point[]; rewear: (Point & { pred: string })[]; centroids: Point[] };
  excluded: { files: string[]; rule: string }; note?: string; features: string;
  sequence_trials?: { label: string; file: string; donning?: number; error?: string; ticks: { top: string; confidence: number; ms: number }[] }[];
  motion_calibration?: import('./meta-sequence').MotionCalibration;
  validation?: { status: 'verified' | 'unverified' | 'calibration'; reason: string; available_counts?: Record<string, number>; donning?: number };
};
export type RunSummary = Pick<Run, 'id' | 'created' | 'labels' | 'same_wear' | 'rewear' | 'rewear_source' | 'shuffled' | 'counts'>;
export type StreamEvent =
  | { type: 'boundary' }
  | { type: 'batch'; emg: number[][]; imu: number[][]; preds: Pred[]; cursor: CursorTick | null; studio?: StudioEvent[]; sampleIndex: number | null; dropped: number; t: number }
  | { type: 'error'; message: string; code?: string };

// EMG Studio 新路由（原力手环 host/studio_api.py，EMG_STUDIO_V2_PLAN 附录 B）。形状跟着服务端，改形状两端一起改。
export type Gate = { ok: boolean; why?: string; frames: number; seconds: number; dropped: number; railed?: number };
export type StudioDevice = {
  device_id: string; name: string; state: string; fs_Hz: number; n_channels: number; labels: string[];
  capabilities: Record<'record' | 'realtime' | 'train' | 'cursor' | 'ab' | 'imu', boolean>;
  segment: number; samples: number; dropped: number; battery: number | null; rig: { kind: string; banner: string; streaming: boolean };
  since: string | null; recording: boolean; session: string | null;
};
export type StudioChannel = { label: string; sensor: string; unit: string; enabled?: boolean };
export type StudioConfig = { id: string; name: string; fs_Hz: number; fs_options: number[]; n_channels: number; channels: StudioChannel[] };
export type StudioSession = { session: string; device_id: string; subject: string; donning: number; hand: string; placement: string; started: string; ended: string | null; n_takes: number };
export type StudioTake = { file: string; label: string; seconds: number; gate: Gate; session: string; device_id: string; donning: number; legacy?: string };
export type StudioFile = { header: { 'sampling rate': number; label: string[] }; from: number; decim: number; n: number; uv: number[][]; events: [number, string, string][] };
export type DatasetSummary = Record<'train' | 'validation' | 'test', Record<string, number>> & { sessions: Record<'train' | 'validation' | 'test', string[]>; rejected: number };
export type StudioDataset = { name: string; created: string; device_id: string | null; summary: DatasetSummary };
export type StudioRun = { id: string; trainer: 'lda' | 'cnn'; dataset: { name: string; fingerprint: string }; device_id: string; labels: string[]; started: string; seconds: number; note?: string;
  metrics: Partial<Record<'train' | 'validation' | 'test', number | null>> };
export type TrainJob = { state: 'idle' | 'running' | 'done' | 'error'; trainer?: string; dataset?: string; run_id?: string; error?: string };
export type FeatureMode = 'bands5' | 'hudgins' | 'combined';
export type GestureState = { feature_modes: FeatureMode[]; min_rms_uv: number; rest_label: string; blackbox_samples: number; blackbox_seconds: number };
/** plugins/rules.py：识别概率 ≥ threshold 连续 hold_ms 触发，cooldown_ms 内不重复；引擎只出事件 */
export type Rule = { id: string; label: string; threshold: number; hold_ms: number; cooldown_ms: number; action: { type: 'key' | 'osc' | 'log'; [k: string]: unknown } };
export type ChannelStats = { n: number; seconds: number | null; channels: { label: string; mean: number; std: number; rms: number; min: number; max: number; median: number; p2p: number }[] };
export type Activation = { index: number; start_s: number; end_s: number; duration_ms: number; peak_uv: number; peak_pct_mvc: number | null; rms_uv: number; median_Hz: number };
export type EmgAnalysis = { fs_Hz: number; seconds: number; channels: { label: string; mvc_uv: number; threshold_uv: number; n_activations: number; activations: Activation[] }[]; csv: string };
/** SSE 推来的带 type / device_id；/api/rules 里的规则事件是引擎原样记录，只有 rule_id / label / p / t */
export type StudioEvent = { type?: 'gate' | 'take' | 'train' | 'rule' | 'lsl'; t: number; device_id?: string; [k: string]: unknown };
export type StudioOps = {
  deviceState: [undefined, StudioDevice];
  deviceConfig: [undefined, StudioConfig];
  deviceConfigPut: [{ channels: { index: number; label?: string; enabled?: boolean }[] }, StudioConfig];
  sessionStart: [{ subject: string; donning: number; hand: Hand; placement: string; notes?: string }, { session: StudioSession }];
  sessionStop: [undefined, { session: string; takes: unknown[] }];
  takeStart: [{ label: string; seconds: number | null }, { take: { label: string; seconds: number | null } }];
  takeStop: [undefined, { file: string | null; gate: Gate | null }];
  takeMark: [{ label: string }, { t_s: number }];
  files: [{ session?: string } | undefined, { sessions: StudioSession[]; takes: StudioTake[] }];
  fileOpen: [{ file: string; from?: number; to?: number; decim?: number }, StudioFile];
  exportTxt: [{ file: string; converted?: boolean }, { name: string }];
  datasets: [undefined, { datasets: StudioDataset[] }];
  datasetSave: [{ name: string; labelMap?: Record<string, string | null> }, { summary: DatasetSummary; rejected: { file: string; why: string }[] }];
  trainStart: [{ dataset: string; trainer: 'lda' | 'cnn'; seed?: number; epochs?: number; featureMode?: FeatureMode }, { ok: true; job: TrainJob }];
  trainRuns: [undefined, { runs: StudioRun[]; job: TrainJob; production: { run_id: string; frozen: string } | null }];
  trainFreeze: [{ runId: string }, { run_id: string; frozen: string }];
  stats: [{ windowS: number }, ChannelStats];
  emgAnalysis: [{ file: string }, EmgAnalysis];
  rules: [undefined, { rules: Rule[]; events: StudioEvent[] }];
  rulesPut: [{ rules: Rule[] }, { rules: Rule[] }];
  lsl: [{ enabled: boolean }, { ok: boolean; enabled: boolean; why?: string; stream_name?: string }];
  gestureState: [undefined, GestureState];
  gestureGate: [{ minRmsUv: number; restLabel?: string }, GestureState];
  gestureFewshot: [{ featureMode?: FeatureMode; k?: number; dataset?: string; labels?: string[] }, { id: string; feature_mode: FeatureMode; k: number; n_base: number; n_calib: number }];
  gestureDump: [undefined, { name: string; samples: number }];
};
export type StudioOp = keyof StudioOps;

export type Emg8Bridge = {
  state: () => Promise<Result<ServiceState>>;
  abState: (a: { hand: Hand; donning: number }) => Promise<Result<AbState>>;
  ab: (projectId: string, a: { action: 'start' | 'pause' | 'resume' | 'stop' | 'void' | 'conditions'; step?: string; hand?: Hand; donning?: number; purpose?: string; placement?: string; conditions?: Conditions | null; strap_hole?: number }) => Promise<Result<Conditions | { ok: true }>>;
  record: (projectId: string, a: { label: string; count: number; set: 'train' | 'rewear'; session?: string; donning: number; countdown?: number; calibration?: boolean; seconds?: number; strap_hole?: number; cable_dir?: string; ch0_site?: string }) => Promise<Result<{ ok: true }>>;
  recordStop: (projectId: string) => Promise<Result<{ ok: true }>>;
  action: (projectId: string, a: { action: 'left_click' | 'right_click' | 'move' | 'scroll'; dx?: number; dy?: number }) => Promise<Result<{ ok: boolean; action?: string; skipped?: string }>>;
  access?: (prompt?: boolean) => Promise<Result<{ trusted: boolean }>>;
  train: (projectId: string, a?: { labels?: string[] }) => Promise<Result<{ ok: true }>>;
  runs: () => Promise<Result<RunSummary[]>>;
  run: (runId: string) => Promise<Result<Run>>;
  live: (projectId: string, a: { action: 'start' | 'stop' | 'tune'; runId?: string; thresholdUv?: number; sensitivity?: number; minProb?: number; thresholdX?: number | null; mask?: number[] }) => Promise<Result<{ ok: true; run_id?: string; threshold_uv?: number; sensitivity?: number; mask?: number[] }>>;
  cursor: (projectId: string, a: { action: 'calibrate' | 'calibrate_pinch' | 'log' | 'enable' | 'stop' | 'drift' | 'config' | 'flip'; stage?: 'move' | 'drag'; gain?: number; deadzone?: number; accel?: number; axis?: 'x' | 'y' } & Partial<CursorOpts>) => Promise<Result<CursorState>>;
  streamStart: (projectId: string) => Promise<Result<true>>;
  streamStop: () => Promise<Result<true>>;
  studio: <K extends StudioOp>(projectId: string, op: K, a?: StudioOps[K][0]) => Promise<Result<StudioOps[K][1]>>;
  onEvent: (cb: (e: StreamEvent) => void) => () => void;
  // 经典 5 步：列 /dev/cu.*、手选数据串口（'' = 自动）、控制串口、打开数据目录、导出这一组
  validation?: (projectId: string, a: Record<string, unknown>) => Promise<Result<{ id: string; active: boolean; reason: string; samples: number; video_chunks: number; video_bytes: number; video_frames: number; finalized: boolean; path: string; host_ms?: number; complete?: boolean }>>;
  ports?: () => Promise<Result<{ list: string[]; selected: string }>>;
  dataPort?: (port: string) => Promise<Result<true>>;
  ctrl?: (projectId: string, a: { action: 'open' | 'close' | 'test'; port?: string; baud?: number }) => Promise<Result<CtrlState>>;
  openData?: (reveal?: boolean) => Promise<Result<string>>;   // 回数据目录路径；reveal 才在访达里打开
  exportClassic?: (a: { labels: string[]; runId?: string | null }) => Promise<Result<{ canceled?: true; path?: string; files?: number }>>;
};

/** 桌面壳里才有；浏览器里是 undefined */
export const emg8Bridge = (): Emg8Bridge | undefined =>
  typeof window === 'undefined' ? undefined : (window as unknown as { pt?: { emg8?: Emg8Bridge } }).pt?.emg8;

const thumbGestures = Object.assign({}, ...Object.values(PROFILES).map((p) => p.gestures ?? {})) as NonNullable<(typeof PROFILES)['thumb-four']['gestures']>;
export { LABEL_CN } from './profiles';   // 定义在 profiles.ts：缺数提示也要用，本文件已从那边取 PROFILES，反过来导入会循环
export const LABEL_ICON: Record<string, string> = { rest: '🖐️', pinch: '🤏', rub: '👌', fist: '✊', left: '👇', right: '👆', click: '🤌', loose: '🩹', ...Object.fromEntries(Object.entries(thumbGestures).map(([k, v]) => [k, v.icon])) };
export const CH_COLORS = [
  '#3B82F6', '#F59E0B', '#22C55E', '#EF4444', '#F97316', '#A855F7', '#06B6D4', '#6366F1',
  '#EC4899', '#14B8A6', '#84CC16', '#EAB308', '#F43F5E', '#8B5CF6', '#0EA5E9', '#10B981',
];
export const CLASS_COLORS: Record<string, string> = { rest: '#94A3B8', pinch: '#22C55E', fist: '#EF4444', rub: '#F59E0B', left: '#3B82F6', right: '#A855F7', click: '#06B6D4', ...Object.fromEntries(Object.entries(thumbGestures).map(([k, v]) => [k, v.color])) };
export const pct = (v: number | null | undefined) => (v == null ? '—' : `${Math.round(v * 100)}%`);
