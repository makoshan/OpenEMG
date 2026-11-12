import CoreBluetooth
import Foundation

// 连 V12 服务（目前只有 XIAO 合成流会自动出数：F05 要先写 TST1/EXT1 等控制命令且硬件锁打开才启动 ADS，
// 本 App 不发控制命令，守住硬件锁），收 F01 包 → 用 F05 同一份 v12_dsp 滤波（HP15/LP600/50Hz 陷波）
// → 每路 100 ms RMS（µV）+ 抽成约 200 点/秒的波形给界面画。

let v12Service = CBUUID(string: "7b24c101-3948-4f03-9d11-12bb9d000001")
let v12Data = CBUUID(string: "7b24c101-3948-4f03-9d11-12bb9d000002")
let v12Meta = CBUUID(string: "7b24c101-3948-4f03-9d11-12bb9d000003")

let fullScaleMicrovolt: Float = 4.0 / 6 * 1_000_000   // ADS1298 默认满量程：参考 4.0 V、增益 6（同 host/v12_ble.py 归档默认参数）
let restMicrovolt: Float = 150
/// 只有这些固件出的是真 ADS 数据；其余（XIAO_SYNTH_PROBE、F04_SYNTHETIC、以后新加的）一律标「合成」。
let realProfiles: Set<String> = ["F05_ADS_CANDIDATE", "F05_ADS1292_2CH_CANDIDATE", "C01_FIXED_CLOCK_LOCKED"]
let allowedVrefMv: Set<Int> = [2400, 2420, 4000, 4033]
let allowedGains: Set<Int> = [1, 2, 3, 4, 6, 8, 12]

private func strictInt(_ value: Any?) -> Int? {
    guard let num = value as? NSNumber,
          CFGetTypeID(num) != CFBooleanGetTypeID(),
          !CFNumberIsFloatType(num),
          Double(num.intValue) == num.doubleValue else { return nil }
    return num.intValue
}

enum F01 {
    /// 一包 → 每帧八路原始码值；格式不对返回 nil。头 16 字节，之后 帧数×27：3 字节状态 + 8×3 字节大端有符号。
    static func frames(_ data: Data) -> [[Int32]]? {
        let b = [UInt8](data)
        guard b.count >= 16, b[0] == 1, b[1] == 1, (1...8).contains(b[2]), b.count == 16 + Int(b[2]) * 27 else { return nil }
        return (0..<Int(b[2])).map { f in   // 已校验长度，下面不会越界
            (0..<8).map { ch in
                let o = 16 + f * 27 + 3 + ch * 3
                let v = Int32(b[o]) << 16 | Int32(b[o + 1]) << 8 | Int32(b[o + 2])
                return v & 0x800000 != 0 ? v - 0x1000000 : v
            }
        }
    }
}

final class Band: NSObject, ObservableObject, CBCentralManagerDelegate, CBPeripheralDelegate {
    static let points = 400                                  // 每路显示约 2 秒
    @Published var status = "等蓝牙"
    @Published var connected = false
    @Published var fps = 0
    @Published var fs = 0
    @Published var live = false                              // 上一秒真收到过帧才算「在出数」
    @Published var source = ""                               // "合成"（XIAO_SYNTH_PROBE）/ "演示"（模拟器）/ ""（真实设备）

    // 下面这些每秒变几百次，不走 @Published，界面用 TimelineView 按帧读
    private(set) var lanes = [[Float]](repeating: [Float](repeating: 0, count: Band.points), count: 8)
    private(set) var head = 0
    private(set) var rms = [Float](repeating: 0, count: 8)   // µV
    private(set) var fullScaleUv: Float = fullScaleMicrovolt

    private var central: CBCentralManager?
    private var peripheral: CBPeripheral?
    private var skipped = Set<UUID>()                        // 元数据不对的设备本次不再连，免得无限重连
    private var dsp = v12_dsp()
    private var bucket = [Float](repeating: 0, count: 8), inBucket = 0
    private var square = [Float](repeating: 0, count: 8), inWindow = 0
    private var counted = 0

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
        var out = [Float](repeating: 0, count: 8), ready: Int32 = 0
        guard raw.withUnsafeBufferPointer({ v12_dsp_frame(&dsp, $0.baseAddress, &out, &ready) }) == 0, ready != 0 else { return }
        for ch in 0..<8 {
            let uv = out[ch] * fullScaleUv
            if abs(uv) > abs(bucket[ch]) { bucket[ch] = uv }
            square[ch] += uv * uv
        }
        inBucket += 1; inWindow += 1
        if inBucket >= max(1, fs / 200) {
            for ch in 0..<8 { lanes[ch][head] = bucket[ch]; bucket[ch] = 0 }
            head = (head + 1) % Band.points; inBucket = 0
        }
        if inWindow >= max(1, fs / 10) {
            for ch in 0..<8 { rms[ch] = (square[ch] / Float(inWindow)).squareRoot(); square[ch] = 0 }
            inWindow = 0
        }
    }

    /// 新连接 / 新会话：滤波器、波形、RMS 和累加器全部清零。fs 只接受 F05 的 2000 / 4000。
    @discardableResult
    func reset(fs: Int) -> Bool {
        guard fs == 2000 || fs == 4000, v12_dsp_init(&dsp, UInt32(fs), 1) == 0 else { return false }
        self.fs = fs
        lanes = [[Float]](repeating: [Float](repeating: 0, count: Band.points), count: 8); head = 0
        rms = [Float](repeating: 0, count: 8)
        bucket = [Float](repeating: 0, count: 8); square = [Float](repeating: 0, count: 8); inBucket = 0; inWindow = 0
        return true
    }

    /// 解析并套用 v12Meta JSON（采样率、真/合成标记、可选 vref_mV/gain 满量程）；不合法一律拒收，不猜参数。
    @discardableResult
    func applyMeta(_ meta: [String: Any]) -> Bool {
        guard let hz = strictInt(meta["fs_Hz"]) else { return false }
        let profile = meta["profile"] as? String ?? ""
        let scale: Float
        if profile == "F05_ADS1292_2CH_CANDIDATE" || meta["vref_mV"] != nil || meta["gain"] != nil {
            guard let vrefMv = strictInt(meta["vref_mV"]), allowedVrefMv.contains(vrefMv),
                  let gain = strictInt(meta["gain"]), allowedGains.contains(gain) else { return false }
            scale = Float(vrefMv) * 1000.0 / Float(gain)
        } else {
            scale = fullScaleMicrovolt
        }
        guard reset(fs: hz) else { return false }
        fullScaleUv = scale
        source = realProfiles.contains(profile) && (meta["synthetic"] as? Bool != true) ? "" : "合成"
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
        rms = [Float](repeating: 0, count: 8)   // 不让旧 RMS 继续冒充放松判定
        if skipped.contains(p.identifier) { c.scanForPeripherals(withServices: [v12Service]); return }   // 保留「元数据不可用」提示
        status = "已断开，重新扫描…"; c.scanForPeripherals(withServices: [v12Service])
    }

    func peripheral(_ p: CBPeripheral, didDiscoverServices error: Error?) {
        guard let s = p.services?.first(where: { $0.uuid == v12Service }) else { return }
        p.discoverCharacteristics([v12Data, v12Meta], for: s)
    }

    func peripheral(_ p: CBPeripheral, didDiscoverCharacteristicsFor s: CBService, error: Error?) {
        // 先读元数据拿采样率，读到后再订阅数据，滤波器才按对的采样率初始化
        if let meta = s.characteristics?.first(where: { $0.uuid == v12Meta }) { p.readValue(for: meta) }
    }

    func peripheral(_ p: CBPeripheral, didUpdateValueFor c: CBCharacteristic, error: Error?) {
        if c.uuid == v12Meta {
            // 元数据不对就停在这里并说清楚，不猜采样率或参考电压（猜错会用错滤波系数和 µV 刻度）
            guard error == nil, let v = c.value, let meta = try? JSONSerialization.jsonObject(with: v) as? [String: Any],
                  applyMeta(meta) else {
                status = "\(p.name ?? "设备") 元数据不可用，已跳过"; skipped.insert(p.identifier); central?.cancelPeripheralConnection(p); return
            }
            if let data = c.service?.characteristics?.first(where: { $0.uuid == v12Data }) { p.setNotifyValue(true, for: data) }
            connected = true; status = "\(p.name ?? "手环") · 等数据"
        } else if c.uuid == v12Data, let v = c.value, let frames = F01.frames(v) {
            if v[v.startIndex + 3] & 2 != 0 { reset(fs: fs) }   // 包头 flags bit1 = 新会话：滤波器重新预热
            if !live { status = p.name ?? "手环" }
            frames.forEach(ingest)
        }
    }

    // MARK: 模拟器演示（没有蓝牙时才走，界面会标「演示」）

    private func startDemo() {
        source = "演示"; connected = true; status = "演示波形"; reset(fs: 2000)
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
