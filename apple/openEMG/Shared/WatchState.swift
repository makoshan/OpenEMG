import Foundation
import SwiftUI
import WatchConnectivity

// iPhone → Watch 的全部状态：一个小 JSON，最新一份覆盖旧的。Watch 只显示，不连手环、不做识别。

let confirmSeconds = 20.0          // 同 host/ai_confirm.py WAIT_S：没手势就拒绝
let gestureNames = ["放松", "唤起", "上滑", "下滑", "左滑", "右滑"]
let gestureHints = ["手自然放松", "中指尖碰拇指", "拇指沿食指朝指尖", "拇指沿食指朝指根", "拇指往左拨", "拇指往右拨"]

struct WatchState: Codable, Equatable {
    var gesture = "放松"
    var confidence = 1.0
    var simulated = true                // 手势是否来自模拟（模型还没上手机）
    var relaxed = true
    var fps = 0
    var pendingCategory: String?
    var pendingHash: String?
    var deadline: Date?
    var result: String?                 // 已同意 / 已拒绝 / 超时拒绝
    var resultAt: Date?

    var isPending: Bool { pendingCategory != nil && (deadline ?? .distantPast) > Date() }
}

enum Palette {
    static let bg = Color(red: 0.04, green: 0.06, blue: 0.07)
    static let card = Color(red: 0.08, green: 0.11, blue: 0.13)
    static let line = Color.white.opacity(0.08)
    static let teal = Color(red: 0.18, green: 0.82, blue: 0.70)
    static let cyan = Color(red: 0.30, green: 0.72, blue: 0.95)
    static let amber = Color(red: 0.98, green: 0.72, blue: 0.27)
    static let coral = Color(red: 0.96, green: 0.42, blue: 0.36)
    static let dim = Color.white.opacity(0.55)
    /// 2 / 8 / 16 路从青绿渐到天蓝，相邻通道一眼分得开
    static func lane(_ i: Int, total: Int = 8) -> Color {
        let denom = Double(max(1, total - 1))
        let k = min(1.0, max(0.0, Double(i) / denom))
        return Color(red: 0.18 + 0.12 * k, green: 0.82 - 0.10 * k, blue: 0.70 + 0.25 * k)
    }
}

/// 两端共用的 WCSession 外壳：iPhone 调 send，Watch 订阅 onState。
final class Link: NSObject, WCSessionDelegate {
    static let shared = Link()
    var onState: ((WatchState) -> Void)?

    func activate() {
        guard WCSession.isSupported() else { return }
        WCSession.default.delegate = self
        WCSession.default.activate()
    }

    func send(_ s: WatchState) {
        guard WCSession.isSupported(), WCSession.default.activationState == .activated,
              let data = try? JSONEncoder().encode(s) else { return }
        let msg = ["s": data]
        if WCSession.default.isReachable { WCSession.default.sendMessage(msg, replyHandler: nil, errorHandler: nil) }
        try? WCSession.default.updateApplicationContext(msg)   // 手表 App 没开时，打开就拿到最新一份
    }

    private func receive(_ msg: [String: Any]) {
        guard let data = msg["s"] as? Data, let s = try? JSONDecoder().decode(WatchState.self, from: data) else { return }
        DispatchQueue.main.async { self.onState?(s) }
    }

    func session(_ s: WCSession, activationDidCompleteWith st: WCSessionActivationState, error: Error?) {
        if !s.receivedApplicationContext.isEmpty { receive(s.receivedApplicationContext) }
    }
    func session(_ s: WCSession, didReceiveMessage m: [String: Any]) { receive(m) }
    func session(_ s: WCSession, didReceiveApplicationContext c: [String: Any]) { receive(c) }
    #if os(iOS)
    func sessionDidBecomeInactive(_ s: WCSession) {}
    func sessionDidDeactivate(_ s: WCSession) { s.activate() }
    #endif
}
