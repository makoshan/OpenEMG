import Foundation

// 手势与 AI 确认的状态。手势模型还没移植到手机，这里先由「模拟」按钮注入，界面会标「模拟」。
// 确认规则同 host/ai_confirm.py：食指碰拇指 = 同意，中指碰拇指 = 拒绝，20 秒没手势 = 拒绝。

final class Gestures: ObservableObject {
    @Published var probs = [1.0, 0, 0, 0, 0, 0]
    @Published var state = WatchState()
    private var restToken = 0

    var current: Int { probs.indices.max { probs[$0] < probs[$1] } ?? 0 }

    /// 模拟做了一次手势：该类 0.9，其余平分，1.2 秒后回到放松。
    func simulate(_ i: Int) {
        probs = gestureNames.indices.map { $0 == i ? 0.9 : 0.1 / Double(gestureNames.count - 1) }
        publish()
        restToken += 1
        let token = restToken
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) { [weak self] in
            guard let self, self.restToken == token else { return }
            self.probs = [1.0, 0, 0, 0, 0, 0]; self.publish()
        }
    }

    /// 模拟一条 AI 待确认（等真钩子接进来之前用它看 Watch 上的确认卡）。
    func simulatePending() {
        state.pendingCategory = "npm 检查"
        state.pendingHash = String(format: "%08x", UInt32.random(in: 0...UInt32.max))
        state.deadline = Date().addingTimeInterval(confirmSeconds)
        state.result = nil
        publish()
        let hash = state.pendingHash
        DispatchQueue.main.asyncAfter(deadline: .now() + confirmSeconds) { [weak self] in
            if self?.state.pendingHash == hash, self?.state.pendingCategory != nil { self?.decide(nil) }
        }
    }

    /// allow：true 同意 / false 拒绝 / nil 超时拒绝。
    func decide(_ allow: Bool?) {
        guard state.pendingCategory != nil else { return }
        state.pendingCategory = nil; state.pendingHash = nil; state.deadline = nil
        state.result = allow == true ? "已同意" : allow == false ? "已拒绝" : "超时拒绝"
        state.resultAt = Date()
        publish()
    }

    /// 把当前手势 + 处理结果（放松与否、帧率）同步给 Watch。
    func publish(relaxed: Bool? = nil, fps: Int? = nil) {
        state.gesture = gestureNames[current]
        state.confidence = probs[current]
        if let relaxed { state.relaxed = relaxed }
        if let fps { state.fps = fps }
        Link.shared.send(state)
    }
}
