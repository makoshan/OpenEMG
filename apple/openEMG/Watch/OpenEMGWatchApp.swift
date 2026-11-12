import SwiftUI
import WatchKit

// 手表只显示 iPhone 发来的状态：平时是当前手势；有 AI 待确认时切到确认卡（D3），并震一下。

final class WatchModel: ObservableObject {
    @Published var state = WatchState()
    init() {
        Link.shared.onState = { [weak self] s in
            guard let self else { return }
            if s.isPending && s.pendingHash != self.state.pendingHash { WKInterfaceDevice.current().play(.notification) }
            if let at = s.resultAt, at != self.state.resultAt, Date().timeIntervalSince(at) < 3 {   // 刚打开时读到的旧结果不震
                WKInterfaceDevice.current().play(s.result == "已同意" ? .success : .failure)
            }
            self.state = s
        }
        Link.shared.activate()
    }
}

@main
struct OpenEMGWatchApp: App {
    @StateObject private var model = WatchModel()
    var body: some Scene { WindowGroup { WatchRoot().environmentObject(model) } }
}

struct WatchRoot: View {
    @EnvironmentObject var model: WatchModel
    var body: some View {
        TimelineView(.periodic(from: .now, by: 1)) { ctx in
            let s = model.state
            Group {
                if s.isPending { ConfirmCard(state: s, now: ctx.date) }
                else if let r = s.result, let at = s.resultAt, ctx.date.timeIntervalSince(at) < 3 { ResultView(text: r) }
                else { GestureView(state: s) }
            }
            .animation(.spring(duration: 0.3), value: s.isPending)
        }
        .containerBackground(Palette.bg.gradient, for: .navigation)
    }
}

struct GestureView: View {
    let state: WatchState
    var body: some View {
        VStack(spacing: 6) {
            ZStack {
                Circle().stroke(Palette.line, lineWidth: 6)
                Circle().trim(from: 0, to: state.confidence)
                    .stroke(Palette.teal, style: StrokeStyle(lineWidth: 6, lineCap: .round)).rotationEffect(.degrees(-90))
                VStack(spacing: 0) {
                    Text(state.gesture).font(.system(size: 30, weight: .bold, design: .rounded)).contentTransition(.numericText())
                    Text(String(format: "%.2f", state.confidence)).font(.system(size: 13, design: .rounded).monospacedDigit()).foregroundStyle(Palette.dim)
                }
            }
            .frame(width: 118, height: 118)
            HStack(spacing: 6) {
                Text(state.fps == 0 ? "未出数" : state.relaxed ? "手放松" : "在用力")
                    .foregroundStyle(state.fps == 0 ? Palette.dim : state.relaxed ? Palette.teal : Palette.amber)
                Text("· \(state.fps) 帧/s").foregroundStyle(Palette.dim)
                if state.simulated { Text("模拟").foregroundStyle(Palette.amber) }
            }
            .font(.system(size: 12, weight: .semibold, design: .rounded))
        }
    }
}

struct ConfirmCard: View {
    let state: WatchState
    let now: Date
    var body: some View {
        let left = max(0, (state.deadline ?? now).timeIntervalSince(now))
        VStack(spacing: 6) {
            Text("AI 待确认").font(.system(size: 13, weight: .semibold)).foregroundStyle(Palette.amber)
            ZStack {
                Circle().stroke(Palette.line, lineWidth: 5)
                Circle().trim(from: 0, to: left / confirmSeconds).stroke(Palette.amber, style: StrokeStyle(lineWidth: 5, lineCap: .round))
                    .rotationEffect(.degrees(-90)).animation(.linear(duration: 1), value: left)
                VStack(spacing: 2) {
                    Text(state.pendingCategory ?? "").font(.system(size: 17, weight: .bold, design: .rounded))
                    Text(state.pendingHash ?? "").font(.system(size: 10, design: .monospaced)).foregroundStyle(Palette.dim)
                    Text("\(Int(left.rounded(.up)))s").font(.system(size: 15, weight: .semibold, design: .rounded).monospacedDigit())
                }
            }
            .frame(width: 104, height: 104)
            HStack(spacing: 10) {
                Label("食指同意", systemImage: "checkmark").foregroundStyle(Palette.teal)
                Label("中指拒绝", systemImage: "xmark").foregroundStyle(Palette.coral)
            }
            .font(.system(size: 11, weight: .semibold)).labelStyle(.titleOnly)
        }
    }
}

struct ResultView: View {
    let text: String
    var body: some View {
        let ok = text == "已同意"
        VStack(spacing: 8) {
            Image(systemName: ok ? "checkmark.circle.fill" : "xmark.circle.fill")
                .font(.system(size: 52)).foregroundStyle(ok ? Palette.teal : Palette.coral)
            Text(text).font(.system(size: 18, weight: .bold, design: .rounded))
        }
    }
}
