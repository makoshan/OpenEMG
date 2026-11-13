import Foundation

// Mac 自检：拆 F01 v1/v4 包 + 走 v12_dsp / c08b_dsp + 测 C08B 冷启动待机与 2/8/16 路热切重读门。用法见 README。
func packet(_ frames: [[Int32]], flags: UInt8 = 2) -> Data {
    var b: [UInt8] = [1, 1, UInt8(frames.count), flags, 0, 0, 0, 0] + [UInt8](repeating: 0, count: 8)
    for f in frames {
        b += [0xC0, 0, 0]
        for v in f {
            let u = UInt32(bitPattern: v) & 0xFFFFFF
            b += [UInt8(u >> 16), UInt8(u >> 8 & 0xFF), UInt8(u & 0xFF)]
        }
    }
    return Data(b)
}

func packetV4(_ frames: [[Int32]], flags: UInt8 = 2) -> Data {
    var b: [UInt8] = [4, 1, UInt8(frames.count), flags, 0, 0, 0, 0] + [UInt8](repeating: 0, count: 8)
    for f in frames {
        precondition(f.count == 16)
        b += [0xC0, 0x01, 0x02]  // U1 状态字（3B）
        for ch in 0..<8 {
            let u = UInt32(bitPattern: f[ch]) & 0xFFFFFF
            b += [UInt8(u >> 16), UInt8(u >> 8 & 0xFF), UInt8(u & 0xFF)]
        }
        b += [0xC0, 0xAA, 0x55]  // U2 状态字（3B，验证偏移 30 跳过第 2 颗芯片状态头）
        for ch in 8..<16 {
            let u = UInt32(bitPattern: f[ch]) & 0xFFFFFF
            b += [UInt8(u >> 16), UInt8(u >> 8 & 0xFF), UInt8(u & 0xFF)]
        }
    }
    return Data(b)
}

let sample: [[Int32]] = [[0, 1, -1, 8388607, -8388608, 123456, -654321, 42], [7, 6, 5, 4, 3, 2, 1, 0]]
precondition(F01.frames(packet(sample)) == sample, "v1 拆包结果不对")
precondition(F01.frames(packet(sample).dropLast()) == nil, "长度不对的包没拒")
var bad = [UInt8](packet(sample)); bad[2] = 9
precondition(F01.frames(Data(bad)) == nil, "v1 帧数超过 8 没拒")
var badFlags = [UInt8](packet(sample, flags: 0x04)) // RECONFIGURE 不带 SESSION_START
precondition(F01.frames(Data(badFlags)) == nil, "RECONFIGURE 缺少 SESSION_START 没拒")
var badFlagsHi = [UInt8](packet(sample, flags: 0x10))
precondition(F01.frames(Data(badFlagsHi)) == nil, "包头保留位非 0 没拒")

let sample16: [[Int32]] = [
    [0, 1, -1, 8388607, -8388608, 111111, -222222, 33, -44, 555555, -666666, 777777, -888888, 999, -1000, 2048],
    (0..<16).map { Int32(($0 + 1) * -321) }
]
precondition(F01.frames(packetV4(sample16)) == sample16, "v4 16 路无损双片拆包不对（核 U2 状态头偏移 30）")
precondition(F01.frames(packetV4(sample16).dropLast()) == nil, "v4 长度不对没拒")
var badV4 = [UInt8](packetV4(sample16)); badV4[2] = 5
precondition(F01.frames(Data(badV4)) == nil, "v4 帧数超过 4 没拒")
var badV1Stat = [UInt8](packet(sample)); badV1Stat[16] = 0x80
precondition(F01.frames(Data(badV1Stat)) == nil, "v1 状态首字节高半字节非 0xC 没拒")
var badV4Stat2 = [UInt8](packetV4(sample16)); badV4Stat2[16 + 27] = 0x00
precondition(F01.frames(Data(badV4Stat2)) == nil, "v4 第 2 颗芯片状态首字节高半字节非 0xC 没拒")

// 滤波：50 Hz、幅度 ±100000 码（约 7.9 mV）正弦过陷波后应大幅衰减；200 Hz 应基本保留
func rms(_ hz: Double) -> Float {
    var dsp = v12_dsp(); v12_dsp_init(&dsp, 2000, 1)
    var out = [Float](repeating: 0, count: 8), ready: Int32 = 0, sum: Float = 0, n: Float = 0
    for i in 0..<4000 {
        let v = Int32(100000 * sin(2 * .pi * hz * Double(i) / 2000))
        let raw = [Int32](repeating: v, count: 8)
        _ = raw.withUnsafeBufferPointer { v12_dsp_frame(&dsp, $0.baseAddress, &out, &ready) }
        if i >= 2000 { sum += out[0] * out[0]; n += 1 }
    }
    return (sum / n).squareRoot() * fullScaleMicrovolt
}
let r50 = rms(50), r200 = rms(200)
precondition(r200 > 3000 && r50 < r200 / 20, "滤波不对：50 Hz \(r50) µV，200 Hz \(r200) µV")

// ingest：4 kHz 喂 3 秒 200 Hz 正弦，预热后每 20 帧抽一点、每 400 帧更新一次 RMS
let band = Band(bluetooth: false)
precondition(!band.reset(fs: 1500) && !band.reset(fs: 250) && band.reset(fs: 500) && band.reset(fs: 1000) && band.reset(fs: 4000),
             "采样率白名单不对")
var dsp = v12_dsp(); v12_dsp_init(&dsp, 4000, 1); var warm = 0, tmp = [Float](repeating: 0, count: 8), rdy: Int32 = 0
for i in 0..<12000 {
    let raw = [Int32](repeating: Int32(100000 * sin(2 * .pi * 200 * Double(i) / 4000)), count: 8)
    band.ingest(raw)
    _ = raw.withUnsafeBufferPointer { v12_dsp_frame(&dsp, $0.baseAddress, &tmp, &rdy) }; if rdy != 0 { warm += 1 }
}
precondition(band.head == (warm / 20) % Band.points, "抽点不对：head \(band.head)，预计 \((warm / 20) % Band.points)")
precondition(band.rms.allSatisfy { abs($0 - r200) / r200 < 0.05 }, "RMS 不对：\(band.rms)")
band.reset(fs: 4000)
precondition(band.head == 0 && band.rms.allSatisfy { $0 == 0 }, "reset 没清干净")

// ADS1292 两路板元数据（F05_ADS1292_2CH_CANDIDATE，vref_mV=2420, gain=6）：识别为真 ADS、两路通道、刻度为 4.0V 的 2.42/4.0 倍
let band1292 = Band(bluetooth: false)
let meta1292: [String: Any] = ["profile": "F05_ADS1292_2CH_CANDIDATE", "fs_Hz": 2000, "vref_mV": 2420, "gain": 6]
precondition(band1292.applyMeta(meta1292) && band1292.source == "" && band1292.channelCount == 2,
             "ADS1292 元数据未识别为两路真实候选固件")
precondition(abs(band1292.fullScaleUv - 403_333.34) < 1.0, "ADS1292 满量程不对：\(band1292.fullScaleUv)")
for i in 0..<6000 {
    let v = Int32(100000 * sin(2 * .pi * 200 * Double(i) / 2000))
    band1292.ingest([v, -v, 0, 0, 0, 0, 0, 0])
}
let expected1292 = r200 * (2.42 / 4.0)
let rms1292 = band1292.rms[0]
precondition(band1292.rms.count == 2 && abs(rms1292 - expected1292) / expected1292 < 0.05 && band1292.activeLanes == 2,
             "ADS1292 两路 RMS 或活跃通道数不对：\(band1292.rms)")
precondition(!band1292.applyMeta(["profile": "F05_ADS1292_2CH_CANDIDATE", "fs_Hz": 2000]), "ADS1292 缺 vref_mV/gain 没拒")
precondition(!band1292.applyMeta(["profile": "F05_ADS1292_2CH_CANDIDATE", "fs_Hz": 2000, "vref_mV": 3300, "gain": 6]), "非法 vref_mV 没拒")
precondition(!band1292.applyMeta(["profile": "F05_ADS1292_2CH_CANDIDATE", "fs_Hz": 2000, "vref_mV": 2420.5, "gain": 6]), "小数 vref_mV 没拒")
precondition(!band1292.applyMeta(["profile": "F05_ADS1292_2CH_CANDIDATE", "fs_Hz": 2000, "vref_mV": 2420.0, "gain": 6]), "浮点 2420.0 没拒")
precondition(!band1292.applyMeta(["profile": "F05_ADS1292_2CH_CANDIDATE", "fs_Hz": 2000, "vref_mV": 2420, "gain": 6.0]), "浮点 6.0 没拒")
let jsonFloat = try! JSONSerialization.jsonObject(with: Data("{\"profile\":\"F05_ADS1292_2CH_CANDIDATE\",\"fs_Hz\":2000.0,\"vref_mV\":2420,\"gain\":6}".utf8)) as! [String: Any]
precondition(!band1292.applyMeta(jsonFloat), "JSON 浮点 2000.0 没拒")
precondition(!band1292.applyMeta(["profile": "F05_ADS1292_2CH_CANDIDATE", "fs_Hz": 2000, "vref_mV": 2420, "gain": 5]), "非法 gain 没拒")
precondition(!band1292.applyMeta(["profile": "F05_ADS_CANDIDATE", "fs_Hz": 1000]), "F05 8 路固件非法 1000 Hz 没拒")
precondition(!band1292.applyMeta(["profile": "F05_ADS_CANDIDATE", "fs_Hz": true]), "布尔 fs_Hz 没拒")
precondition(band1292.applyMeta(["profile": "F05_ADS_CANDIDATE", "fs_Hz": 2000]) && band1292.source == "" && band1292.channelCount == 8 && band1292.fullScaleUv == fullScaleMicrovolt,
             "切换回 F05_ADS_CANDIDATE 未恢复 8 路默认满量程")
precondition(band1292.applyMeta(["profile": "XIAO_SYNTH_PROBE", "fs_Hz": 2000, "synthetic": true]) && band1292.source == "合成", "合成流未标合成")

// C08B 共用双核主控（冷启动 afe=NONE -> 16 路 1 kHz 合成/真流 -> RECONFIGURE 热切 8 路 500 Hz -> 2 路 1 kHz）
let bandC08B = Band(bluetooth: false)
let metaIdle: [String: Any] = [
    "profile": "C08B_DUAL_STREAM_CANDIDATE", "board": "C08B_R4U6", "afe": "NONE",
    "protocol": 1, "channels": 8, "active_channels": 0, "fs_Hz": 1000, "vref_mV": 2400, "gain": 6
]
precondition(bandC08B.applyMeta(metaIdle) && bandC08B.standby && !bandC08B.needsMetaRefresh, "C08B 冷启动待机元数据未识别")
// 待机态收到首包 16 路数据：必须拒收并锁存 needsMetaRefresh，等重读 META 后才放行（含后续无 RECONFIGURE 标志的续包）
let pkt16Start = packetV4([(0..<16).map { Int32($0 * 100) }], flags: 0x03) // SYNTHETIC | SESSION_START
let pkt16Cont  = packetV4([(0..<16).map { Int32($0 * 100) }], flags: 0x01) // SYNTHETIC 续包
precondition(!bandC08B.receiveDataPacket(pkt16Start) && bandC08B.needsMetaRefresh, "待机态首包未触发重读 META")
precondition(!bandC08B.receiveDataPacket(pkt16Cont) && bandC08B.needsMetaRefresh, "重读完成前续包不应放行")

// 重读拿到 16 路 1000 Hz 元数据（vref=2400 mV, gain=6 -> 400_000 µV）
let meta16: [String: Any] = [
    "profile": "C08B_DUAL_STREAM_CANDIDATE", "board": "C08B_R4U6", "afe": "ADS1298_DUAL",
    "protocol": 4, "channels": 16, "active_channels": 16, "fs_Hz": 1000, "vref_mV": 2400, "gain": 6
]
precondition(bandC08B.applyMeta(meta16) && !bandC08B.standby && !bandC08B.needsMetaRefresh
             && bandC08B.channelCount == 16 && bandC08B.wireChannels == 16 && abs(bandC08B.fullScaleUv - 400_000) < 1,
             "C08B 16 路元数据套用不对")
// SYN1 包头带 SYNTHETIC(bit0=1) 时，即使 profile 在白名单中也必须强制标「合成」
precondition(bandC08B.receiveDataPacket(pkt16Start) && bandC08B.source == "合成", "C08B SYN1 包头 SYNTHETIC 未强制标合成")

// 喂 3 秒（3000 帧 @ 1000 Hz）：CH1..8 为 200 Hz 通带正弦，CH9..16 为 50 Hz 工频正弦（检验第 2 组滤波器与 50 Hz 陷波）
let startPkt16Real = packetV4([Array(repeating: 0, count: 16)], flags: 0x02) // 真流 SESSION_START，清除合成标
precondition(bandC08B.receiveDataPacket(startPkt16Real) && bandC08B.source == "", "C08B 真流未恢复真实标记")
for i in 0..<3000 {
    let v200 = Int32(100000 * sin(2 * .pi * 200 * Double(i) / 1000))
    let v50  = Int32(100000 * sin(2 * .pi * 50  * Double(i) / 1000))
    let frame = (0..<16).map { $0 < 8 ? v200 : v50 }
    precondition(bandC08B.receiveDataPacket(packetV4([frame], flags: 0)))
}
let expectedC08B200 = r200 * (2.40 / 4.0)
let r16Pass = bandC08B.rms[0], r16Notch = bandC08B.rms[15]
precondition(bandC08B.rms[0..<8].allSatisfy { abs($0 - expectedC08B200) / expectedC08B200 < 0.08 },
             "C08B 16 路前 8 路 1 kHz 通带 RMS 不对：\(bandC08B.rms[0..<8])，预计 \(expectedC08B200)")
precondition(bandC08B.rms[8..<16].allSatisfy { $0 < r16Pass / 20 },
             "C08B 16 路后 8 路 1 kHz 50 Hz 陷波未生效：\(bandC08B.rms[8..<16])")
precondition(bandC08B.activeLanes == 8, "C08B 16 路活跃通道数应为 8，实际 \(bandC08B.activeLanes)")

// 16 路滤波器原子越界保护：第 13 路（第 2 组）越界时，第 1 组状态不得推进
var dsp16 = c08b_dsp(); precondition(c08b_dsp_init(&dsp16, 1000, 16, 1) == 0)
var out16 = [Float](repeating: 0, count: 16), rdy16: Int32 = 0
var badCodeFrame = [Int32](repeating: 1000, count: 16); badCodeFrame[12] = 9_000_000
let rcBad = badCodeFrame.withUnsafeBufferPointer { c08b_dsp_frame(&dsp16, $0.baseAddress, 16, &out16, &rdy16) }
precondition(rcBad == Int32(V12_DSP_CODE_RANGE) && dsp16.bank.0.processed == 0 && dsp16.bank.1.processed == 0,
             "16 路第 2 组码值越界时第 1 组状态不应推进")

// 同连接内 RECONFIGURE(0x06) 热切到 8 路 500 Hz：首包和未重读前的无标志第 2 包都必须拦截
let pkt8Reconf = packet([[Int32](repeating: 500, count: 8)], flags: 0x06)
let pkt8Cont   = packet([[Int32](repeating: 500, count: 8)], flags: 0x00)
precondition(!bandC08B.receiveDataPacket(pkt8Reconf) && bandC08B.needsMetaRefresh, "RECONFIGURE 包未锁存重读门")
precondition(!bandC08B.receiveDataPacket(pkt8Cont) && bandC08B.needsMetaRefresh, "RECONFIGURE 后未重读 META 前的续包被放行")

let meta8_500: [String: Any] = [
    "profile": "C08B_DUAL_STREAM_CANDIDATE", "board": "C08B_R4U6", "afe": "ADS1298_SINGLE",
    "protocol": 1, "channels": 8, "active_channels": 8, "fs_Hz": 500, "vref_mV": 2400, "gain": 6
]
precondition(bandC08B.applyMeta(meta8_500) && bandC08B.channelCount == 8 && bandC08B.fs == 500, "C08B 8 路 500 Hz 元数据套用失败")
for i in 0..<1500 {
    let v120 = Int32(100000 * sin(2 * .pi * 120 * Double(i) / 500))
    let v50  = Int32(100000 * sin(2 * .pi * 50  * Double(i) / 500))
    let frame = (0..<8).map { $0 < 4 ? v120 : v50 }
    precondition(bandC08B.receiveDataPacket(packet([frame], flags: i == 0 ? 0x02 : 0x00)))
}
precondition(bandC08B.rms[0] > 2500 && bandC08B.rms[4] < bandC08B.rms[0] / 20 && bandC08B.activeLanes == 4,
             "C08B 8 路 500 Hz 通带/陷波不对：\(bandC08B.rms)")

// 非法 C08B 元数据组合必须拒绝（例如 ADS1298_DUAL 却写 protocol=1，或 afe=NONE 却写 active_channels=8）
precondition(!bandC08B.applyMeta([
    "profile": "C08B_DUAL_STREAM_CANDIDATE", "afe": "ADS1298_DUAL",
    "protocol": 1, "channels": 16, "active_channels": 16, "fs_Hz": 1000, "vref_mV": 2400, "gain": 6
]), "C08B protocol=1 与 16 路冲突没拒")
precondition(!bandC08B.applyMeta([
    "profile": "C08B_DUAL_STREAM_CANDIDATE", "afe": "NONE",
    "protocol": 1, "channels": 8, "active_channels": 8, "fs_Hz": 1000, "vref_mV": 2400, "gain": 6
]), "C08B afe=NONE 与非零 active_channels 冲突没拒")

print(String(format: "openEMG check 通过：v1/v4 拆包与反例；200 Hz %.0f µV、50 Hz %.0f µV；ADS1292 两路 %.0f µV；C08B 16 路@1kHz %.0f/%.0f µV、8 路@500Hz %.0f/%.0f µV、待机与热切锁存门通过",
             r200, r50, rms1292, r16Pass, r16Notch, bandC08B.rms[0], bandC08B.rms[4]))
