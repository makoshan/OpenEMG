import Foundation

// Mac 自检：拆 F01 包 + 走 v12_dsp。用法见 README。
func packet(_ frames: [[Int32]]) -> Data {
    var b: [UInt8] = [1, 1, UInt8(frames.count), 2, 0, 0, 0, 0] + [UInt8](repeating: 0, count: 8)
    for f in frames { b += [0xC0, 0, 0]; for v in f { let u = UInt32(bitPattern: v) & 0xFFFFFF; b += [UInt8(u >> 16), UInt8(u >> 8 & 0xFF), UInt8(u & 0xFF)] } }
    return Data(b)
}
let sample: [[Int32]] = [[0, 1, -1, 8388607, -8388608, 123456, -654321, 42], [7, 6, 5, 4, 3, 2, 1, 0]]
precondition(F01.frames(packet(sample)) == sample, "拆包结果不对")
precondition(F01.frames(packet(sample).dropLast()) == nil, "长度不对的包没拒")
var bad = [UInt8](packet(sample)); bad[2] = 9
precondition(F01.frames(Data(bad)) == nil, "帧数超过 8 没拒")

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
precondition(!band.reset(fs: 1000) && band.reset(fs: 4000), "采样率白名单不对")
var dsp = v12_dsp(); v12_dsp_init(&dsp, 4000, 1); var warm = 0, tmp = [Float](repeating: 0, count: 8), rdy: Int32 = 0
for i in 0..<12000 {
    let raw = [Int32](repeating: Int32(100000 * sin(2 * .pi * 200 * Double(i) / 4000)), count: 8)
    band.ingest(raw)
    _ = raw.withUnsafeBufferPointer { v12_dsp_frame(&dsp, $0.baseAddress, &tmp, &rdy) }; if rdy != 0 { warm += 1 }
}
precondition(band.head == (warm / 20) % Band.points, "抽点不对：head \(band.head)，预计 \((warm / 20) % Band.points)")
precondition(band.rms.allSatisfy { abs($0 - r200) / r200 < 0.05 }, "RMS 不对：\(band.rms)")
let rmsBefore = band.rms[0]
band.reset(fs: 4000)
precondition(band.head == 0 && band.rms.allSatisfy { $0 == 0 }, "reset 没清干净")
print(String(format: "openEMG check 通过：拆包 3 例；滤波 200 Hz %.0f µV、50 Hz %.0f µV（陷波后）；4 kHz 抽点 %d 点、RMS %.0f µV、reset 清零", r200, r50, warm / 20, rmsBefore))
