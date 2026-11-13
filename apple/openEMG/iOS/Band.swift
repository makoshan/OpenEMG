import CoreBluetooth
import Foundation

// 连 V12 服务（R01 F05、ADS1292 2CH、C08B 共用双核主控 2/8/16CH 均走同一套 UUID；
// 真设备需台架/主机控制端开启采集且硬件锁放行后才出真 ADS 数据，本 App 不发控制命令，守住硬件锁），
// 收 F01 v1（8/2 路）或 v4（16 路无损双片）包 → 走 v12_dsp / c08b_dsp 滤波 → 每路 100 ms RMS（µV）+ 约 200 点/秒波形。

let v12Service = CBUUID(string: "7b24c101-3948-4f03-9d11-12bb9d000001")
let v12Data = CBUUID(string: "7b24c101-3948-4f03-9d11-12bb9d000002")
let v12Meta = CBUUID(string: "7b24c101-3948-4f03-9d11-12bb9d000003")

let fullScaleMicrovolt: Float = 4.0 / 6 * 1_000_000   // ADS1298 R01 默认满量程：参考 4.0 V、增益 6（同 host/v12_ble.py 归档默认参数）
let restMicrovolt: Float = 150
/// 只有这些固件在非合成模式下出的是真 ADS 数据；其余（XIAO_SYNTH_PROBE、F04_SYNTHETIC 或包头带 SYNTHETIC 标志）一律标「合成」。
let realProfiles: Set<String> = [
    "F05_ADS_CANDIDATE",
    "F05_ADS1292_2CH_CANDIDATE",
    "C08B_DUAL_STREAM_CANDIDATE",
    "C01_FIXED_CLOCK_LOCKED"
]
let allowedVrefMv: Set<Int> = [2400, 2420, 4000, 4033]
let allowedGains: Set<Int> = [1, 2, 3, 4, 6, 8, 12]
let allowedSampleRates: Set<Int> = [500, 1000, 2000, 4000]

private func strictInt(_ value: Any?) -> Int? {
    guard let num = value as? NSNumber,
          CFGetTypeID(num) != CFBooleanGetTypeID(),
          !CFNumberIsFloatType(num),
          Double(num.intValue) == num.doubleValue else { return nil }
    return num.intValue
}

private func decodeS24BE(_ b: [UInt8], _ o: Int) -> Int32 {
    let v = Int32(b[o]) << 16 | Int32(b[o + 1]) << 8 | Int32(b[o + 2])
    return v & 0x800000 != 0 ? v - 0x1000000 : v
}

enum F01 {
    /// 一包 → 每帧原始码值；格式不对返回 nil。
    /// - v1（8/2 路）：头 16 字节 + 帧数(1..8)×27（3B 状态 + 8×3B 大端有符号）
    /// - v4（C08B 16 路无损双片）：头 16 字节 + 帧数(1..4)×54（U1: 3B 状态 + 8×3B，U2: 3B 状态 + 8×3B）
    static func frames(_ data: Data) -> [[Int32]]? {
        let b = [UInt8](data)
        guard b.count >= 16, b[1] == 1 else { return nil }
        // RECONFIGURE(bit2) 必须伴随 SESSION_START(bit1)，且高 5 位保留位必须为 0
        guard (b[3] & 0xF8) == 0, (b[3] & 0x04) == 0 || (b[3] & 0x02) != 0 else { return nil }
        let count = Int(b[2])
        if b[0] == 1 {
            guard (1...8).contains(count), b.count == 16 + count * 27 else { return nil }
            for f in 0..<count {
                guard (b[16 + f * 27] & 0xF0) == 0xC0 else { return nil }
            }
            return (0..<count).map { f in
                let base = 16 + f * 27 + 3
                return (0..<8).map { ch in decodeS24BE(b, base + ch * 3) }
            }
        } else if b[0] == 4 {
            guard (1...4).contains(count), b.count == 16 + count * 54 else { return nil }
            for f in 0..<count {
                let base = 16 + f * 54
                guard (b[base] & 0xF0) == 0xC0, (b[base + 27] & 0xF0) == 0xC0 else { return nil }
            }
            return (0..<count).map { f in
                let base = 16 + f * 54
                return (0..<16).map { ch in
                    let o = ch < 8 ? (base + 3 + ch * 3) : (base + 30 + (ch - 8) * 3)
                    return decodeS24BE(b, o)
                }
            }
        }
        return nil
    }
}

final class Band: NSObject, ObservableObject, CBCentralManagerDelegate, CBPeripheralDelegate {
    static let points = 400                                  // 每路显示约 2 秒
    @Published var status = "等蓝牙"
    @Published var connected = false
    @Published var fps = 0
    @Published var fs = 0
    @Published var channelCount = 8                          // 当前有效通道数（2 / 8 / 16）
    @Published var live = false                              // 上一秒真收到过帧才算「在出数」
    @Published var source = ""                               // "合成" / "演示" / ""（真实设备）

    // 下面这些每秒变几百次，不走 @Published，界面用 TimelineView 按帧读
    private(set) var lanes = [[Float]](repeating: [Float](repeating: 0, count: Band.points), count: 8)
    private(set) var head = 0
    private(set) var rms = [Float](repeating: 0, count: 8)   // µV
    private(set) var fullScaleUv: Float = fullScaleMicrovolt
    private(set) var wireChannels = 8                        // 线上每帧通道槽数（v1=8, v4=16）
    private(set) var standby = false                         // C08B 冷启动 afe="NONE" 待机态
    private(set) var needsMetaRefresh = false                // 收到 RECONFIGURE / 待机首包 / 通道切换后锁存，重读 META 前拒收帧

    private var central: CBCentralManager?
    private var peripheral: CBPeripheral?
    private var skipped = Set<UUID>()                        // 元数据不对的设备本次不再连，免得无限重连
    private var dsp = c08b_dsp()
    private var bucket = [Float](repeating: 0, count: 8), inBucket = 0
    private var square = [Float](repeating: 0, count: 8), inWindow = 0
    private var counted = 0
    private var metaIsReal = false
    private var readingMeta = false

    /// bluetooth: false 只给 Mac 自检用（不碰蓝牙权限）。
    init(bluetooth: Bool = true) {
        super.init()
        guard bluetooth else { return }
        central = CBCentralManager(delegate: self, queue: .main)
        Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            guard let self else { return }
            self.fps = self.counted; self.live = self.counted > 0; self.counted = 0
        }
    }

    var demo: Bool { source == "演示" }

    var relaxed: Bool { rms.allSatisfy { $0 < restMicrovolt } }
    var activeLanes: Int { rms.filter { $0 >= restMicrovolt }.count }

    /// 一帧原始码值进来：滤波 → 抽点（每桶取绝对值最大的那个样本，保留正负）→ 累 RMS。
    func ingest(_ raw: [Int32]) {
        counted += 1
        var out = [Float](repeating: 0, count: Int(C08B_DSP_MAX_CHANNELS)), ready: Int32 = 0
        let rc = raw.withUnsafeBufferPointer { buf -> Int32 in
            guard let base = buf.baseAddress else { return -1 }
            return c08b_dsp_frame(&dsp, base, UInt32(buf.count), &out, &ready)
        }
        guard rc == 0, ready != 0 else { return }
        let n = channelCount
        for ch in 0..<n {
            let uv = out[ch] * fullScaleUv
            if abs(uv) > abs(bucket[ch]) { bucket[ch] = uv }
            square[ch] += uv * uv
        }
        inBucket += 1; inWindow += 1
        if inBucket >= max(1, fs / 200) {
            for ch in 0..<n { lanes[ch][head] = bucket[ch]; bucket[ch] = 0 }
            head = (head + 1) % Band.points; inBucket = 0
        }
        if inWindow >= max(1, fs / 10) {
            for ch in 0..<n { rms[ch] = (square[ch] / Float(inWindow)).squareRoot(); square[ch] = 0 }
            inWindow = 0
        }
    }

    /// 新连接 / 新会话：滤波器、波形、RMS 和累加器全部清零。支持 500 / 1000 / 2000 / 4000 Hz 与 2 / 8 / 16 路。
    @discardableResult
    func reset(fs: Int, channels: Int = 8, wireChannels: Int? = nil) -> Bool {
        let wire = wireChannels ?? (channels == 16 ? 16 : 8)
        guard allowedSampleRates.contains(fs),
              (wire == 8 && (channels == 2 || channels == 8)) || (wire == 16 && channels == 16),
              c08b_dsp_init(&dsp, UInt32(fs), UInt32(channels), 1) == 0 else { return false }
        self.fs = fs
        self.channelCount = channels
        self.wireChannels = wire
        lanes = [[Float]](repeating: [Float](repeating: 0, count: Band.points), count: channels); head = 0
        rms = [Float](repeating: 0, count: channels)
        bucket = [Float](repeating: 0, count: channels); square = [Float](repeating: 0, count: channels)
        inBucket = 0; inWindow = 0
        return true
    }

    /// 解析并套用 v12Meta JSON（采样率、通道拓扑、真/合成标记、vref_mV/gain 满量程）；不合法一律拒收，不猜参数。
    @discardableResult
    func applyMeta(_ meta: [String: Any]) -> Bool {
        guard let hz = strictInt(meta["fs_Hz"]), allowedSampleRates.contains(hz) else { return false }
        let profile = meta["profile"] as? String ?? ""
        if profile == "F05_ADS_CANDIDATE" || profile == "C01_FIXED_CLOCK_LOCKED" {
            guard hz == 2000 || hz == 4000 else { return false }
        } else if profile == "F05_ADS1292_2CH_CANDIDATE" || profile == "C08B_DUAL_STREAM_CANDIDATE" {
            guard hz == 500 || hz == 1000 || hz == 2000 else { return false }
        }

        let scale: Float
        if profile == "F05_ADS1292_2CH_CANDIDATE" || profile == "C08B_DUAL_STREAM_CANDIDATE"
            || meta["vref_mV"] != nil || meta["gain"] != nil {
            guard let vrefMv = strictInt(meta["vref_mV"]), allowedVrefMv.contains(vrefMv),
                  let gain = strictInt(meta["gain"]), allowedGains.contains(gain) else { return false }
            scale = Float(vrefMv) * 1000.0 / Float(gain)
        } else {
            scale = fullScaleMicrovolt
        }

        let wire: Int
        if meta["channels"] != nil {
            guard let w = strictInt(meta["channels"]), w == 8 || w == 16 else { return false }
            wire = w
        } else {
            wire = 8
        }
        if meta["protocol"] != nil {
            guard let proto = strictInt(meta["protocol"]),
                  (proto == 1 && wire == 8) || (proto == 4 && wire == 16) else { return false }
        }

        let afe = meta["afe"] as? String ?? ""
        let active: Int
        let isStandby: Bool
        if meta["active_channels"] != nil {
            guard let act = strictInt(meta["active_channels"]) else { return false }
            if act == 0 {
                guard profile == "C08B_DUAL_STREAM_CANDIDATE", afe == "NONE", wire == 8 else { return false }
                active = 8; isStandby = true
            } else {
                guard (wire == 8 && (act == 2 || act == 8)) || (wire == 16 && act == 16) else { return false }
                active = act; isStandby = false
            }
        } else {
            guard afe != "NONE" else { return false }
            active = (profile == "F05_ADS1292_2CH_CANDIDATE" || afe == "ADS1292") ? 2 : wire
            isStandby = false
        }

        if profile == "C08B_DUAL_STREAM_CANDIDATE" && !isStandby {
            let validAfe = (afe == "ADS1292" && active == 2 && wire == 8)
                || (afe == "ADS1298_SINGLE" && active == 8 && wire == 8)
                || (afe == "ADS1298_DUAL" && active == 16 && wire == 16)
            guard validAfe else { return false }
        }

        guard reset(fs: hz, channels: active, wireChannels: wire) else { return false }
        standby = isStandby
        needsMetaRefresh = false
        readingMeta = false
        fullScaleUv = scale
        metaIsReal = realProfiles.contains(profile) && (meta["synthetic"] as? Bool != true)
        source = metaIsReal ? "" : "合成"
        return true
    }

    /// 处理一包 BLE v12Data：若处于冷启动待机、收到 RECONFIGURE(bit2) 或帧宽切换，锁存 needsMetaRefresh 并返回 false
    /// 触发重读 v12Meta，绝不用旧采样率或旧参考电压硬解新流；包头带 SYNTHETIC(bit0) 时强制标「合成」。
    @discardableResult
    func receiveDataPacket(_ data: Data) -> Bool {
        guard let frames = F01.frames(data), let first = frames.first else { return false }
        let flags = data[data.startIndex + 3]
        if standby || needsMetaRefresh || (flags & 0x04) != 0 || first.count != wireChannels {
            needsMetaRefresh = true
            return false
        }
        source = ((flags & 0x01) != 0 || !metaIsReal) ? "合成" : ""
        if (flags & 0x02) != 0 {
            reset(fs: fs, channels: channelCount, wireChannels: wireChannels)
        }
        frames.forEach(ingest)
        return true
    }

    // MARK: 蓝牙

    func centralManagerDidUpdateState(_ c: CBCentralManager) {
        switch c.state {
        case .poweredOn: status = "扫描手环…"; c.scanForPeripherals(withServices: [v12Service])
        case .unsupported:
            #if targetEnvironment(simulator)
            startDemo()
            #else
            status = "这台设备不支持蓝牙"
            #endif
        default: status = "请打开蓝牙"
        }
    }

    func centralManager(_ c: CBCentralManager, didDiscover p: CBPeripheral, advertisementData: [String: Any], rssi: NSNumber) {
        guard !skipped.contains(p.identifier) else { return }
        c.stopScan(); peripheral = p; p.delegate = self
        status = "连接 \(p.name ?? "手环")…"; c.connect(p)
    }

    func centralManager(_ c: CBCentralManager, didConnect p: CBPeripheral) { p.discoverServices([v12Service]) }
    func centralManager(_ c: CBCentralManager, didFailToConnect p: CBPeripheral, error: Error?) { c.scanForPeripherals(withServices: [v12Service]) }
    func centralManager(_ c: CBCentralManager, didDisconnectPeripheral p: CBPeripheral, error: Error?) {
        connected = false; live = false; source = ""; fullScaleUv = fullScaleMicrovolt
        standby = false; needsMetaRefresh = false; readingMeta = false; metaIsReal = false
        rms = [Float](repeating: 0, count: channelCount)   // 不让旧 RMS 继续冒充放松判定
        if skipped.contains(p.identifier) { c.scanForPeripherals(withServices: [v12Service]); return }   // 保留「元数据不可用」提示
        status = "已断开，重新扫描…"; c.scanForPeripherals(withServices: [v12Service])
    }

    func peripheral(_ p: CBPeripheral, didDiscoverServices error: Error?) {
        guard let s = p.services?.first(where: { $0.uuid == v12Service }) else { return }
        p.discoverCharacteristics([v12Data, v12Meta], for: s)
    }

    func peripheral(_ p: CBPeripheral, didDiscoverCharacteristicsFor s: CBService, error: Error?) {
        // 先读元数据拿采样率，读到后再订阅数据，滤波器才按对的采样率初始化
        if let meta = s.characteristics?.first(where: { $0.uuid == v12Meta }) {
            readingMeta = true
            p.readValue(for: meta)
        }
    }

    func peripheral(_ p: CBPeripheral, didUpdateValueFor c: CBCharacteristic, error: Error?) {
        if c.uuid == v12Meta {
            readingMeta = false
            // 元数据不对就停在这里并说清楚，不猜采样率或参考电压（猜错会用错滤波系数和 µV 刻度）
            guard error == nil, let v = c.value, let meta = try? JSONSerialization.jsonObject(with: v) as? [String: Any],
                  applyMeta(meta) else {
                status = "\(p.name ?? "设备") 元数据不可用，已跳过"; skipped.insert(p.identifier); central?.cancelPeripheralConnection(p); return
            }
            if let data = c.service?.characteristics?.first(where: { $0.uuid == v12Data }), !data.isNotifying {
                p.setNotifyValue(true, for: data)
            }
            connected = true
            status = standby ? "\(p.name ?? "手环") · 待机（未开采集）" : "\(p.name ?? "手环") · 等数据"
        } else if c.uuid == v12Data, let v = c.value {
            guard F01.frames(v) != nil else { return }
            if receiveDataPacket(v) {
                if !live { status = p.name ?? "手环" }
            } else if needsMetaRefresh && !readingMeta,
                      let meta = c.service?.characteristics?.first(where: { $0.uuid == v12Meta }) {
                readingMeta = true
                p.readValue(for: meta)
            }
        }
    }

    // MARK: 模拟器演示（没有蓝牙时才走，界面会标「演示」）

    private func startDemo() {
        source = "演示"; connected = true; status = "演示波形"; reset(fs: 2000, channels: 8)
        var t = 0.0
        Timer.scheduledTimer(withTimeInterval: 0.01, repeats: true) { [weak self] _ in
            guard let self else { return }
            for _ in 0..<20 {                                   // 每 10 ms 喂 20 帧 = 2000 帧/秒
                t += 1 / 2000
                let raw: [Int32] = (0..<8).map { ch in
                    let burst = max(0, sin(t * 0.9 + Double(ch) * 0.8)) * (ch % 3 == 0 ? 1 : 0.35)
                    return Int32(Double.random(in: -1...1) * (40 + 3000 * burst))
                }
                self.ingest(raw)
            }
        }
    }
}
