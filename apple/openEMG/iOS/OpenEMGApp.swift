import SwiftUI

@main
struct OpenEMGApp: App {
    @StateObject private var band = Band()
    @StateObject private var gestures = Gestures()
    init() { Link.shared.activate() }

    var body: some Scene {
        WindowGroup {
            MainView().environmentObject(band).environmentObject(gestures)
                .preferredColorScheme(.dark)
                .onAppear { UIApplication.shared.isIdleTimerDisabled = true }   // 看波形时不自动锁屏
        }
    }
}

// MARK: D1 主屏：八路波形为主，底部是当前手势

struct MainView: View {
    @EnvironmentObject var band: Band
    @EnvironmentObject var gestures: Gestures
    @State private var showDetail = false

    var body: some View {
        ZStack {
            Palette.bg.ignoresSafeArea()
            VStack(spacing: 14) {
                header
                if gestures.state.isPending { PendingBanner(state: gestures.state) }
                WaveformCard()
                GestureBar(show: $showDetail)
            }
            .padding(.horizontal, 16).padding(.top, 8).padding(.bottom, 12)
        }
        .sheet(isPresented: $showDetail) { DetailSheet().environmentObject(band).presentationDetents([.large]).presentationDragIndicator(.visible) }
        .onReceive(band.$fps) { gestures.publish(relaxed: band.relaxed, fps: $0) }   // 每秒同步一次处理结果给手表
        .animation(.spring(duration: 0.35), value: gestures.state.isPending)
        .onAppear {   // 截图验证用：启动参数带 -demoPending 时来一条待确认、做一次「唤起」
            if ProcessInfo.processInfo.arguments.contains("-demoPending") { gestures.simulatePending(); gestures.simulate(1) }
        }
    }

    private var header: some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 2) {
                Text("openEMG").font(.system(size: 30, weight: .bold, design: .rounded))
                Text(band.status).font(.footnote).foregroundStyle(Palette.dim)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 6) {
                HStack(spacing: 6) {
                    Circle().fill(band.live ? Palette.teal : Palette.dim).frame(width: 7, height: 7)
                    Text("\(band.fps)").font(.system(.subheadline, design: .rounded).monospacedDigit().weight(.semibold))
                    Text("帧/s").font(.caption2).foregroundStyle(Palette.dim)
                }
                .padding(.horizontal, 10).padding(.vertical, 5).background(Palette.card, in: Capsule())
                RelaxChip()
            }
        }
    }
}

struct RelaxChip: View {
    @EnvironmentObject var band: Band
    var body: some View {
        TimelineView(.periodic(from: .now, by: 0.2)) { _ in
            let relaxed = band.relaxed
            let tint = !band.live ? Palette.dim : relaxed ? Palette.teal : Palette.amber   // 未出数用灰色，和手表一致
            HStack(spacing: 6) {
                if !band.source.isEmpty { Text(band.source).font(.caption2.weight(.bold)).foregroundStyle(Palette.bg)
                    .padding(.horizontal, 5).background(Palette.dim, in: Capsule()) }
                Text(!band.live ? "未出数" : relaxed ? "手放松" : "在用力 · \(band.activeLanes) 路")
                    .font(.caption.weight(.semibold)).foregroundStyle(tint)
            }
            .padding(.horizontal, 10).padding(.vertical, 4)
            .background(tint.opacity(0.14), in: Capsule())
        }
    }
}

struct WaveformCard: View {
    @EnvironmentObject var band: Band
    var body: some View {
        TimelineView(.animation(minimumInterval: 1 / 30)) { _ in
            Canvas { ctx, size in
                let count = max(1, min(band.channelCount, min(band.lanes.count, band.rms.count)))
                let rowH = size.height / CGFloat(count), meterW: CGFloat = 64
                let labelW: CGFloat = count > 9 ? 34 : 30
                let fontSize: CGFloat = count > 8 ? 8.5 : 10
                let barH: CGFloat = count > 8 ? 4.5 : 6
                let waveW = size.width - meterW - labelW - 8
                // 全路共用一个量程，通道之间才能比大小；最小 300 µV，免得底噪被放大成满屏
                let peak = max(300, band.lanes.prefix(count).lazy.flatMap { $0 }.map { abs($0) }.max() ?? 0)
                for ch in 0..<count {
                    let midY = rowH * (CGFloat(ch) + 0.5)
                    ctx.draw(Text("CH\(ch + 1)").font(.system(size: fontSize, weight: .semibold, design: .monospaced))
                        .foregroundColor(Palette.dim), at: CGPoint(x: labelW * 0.48, y: midY))
                    var line = Path(), lane = band.lanes[ch]
                    for i in 0..<Band.points {
                        let v = lane[(band.head + i) % Band.points]
                        let p = CGPoint(x: labelW + waveW * CGFloat(i) / CGFloat(Band.points - 1),
                                        y: midY - CGFloat(v / peak) * rowH * 0.46)
                        i == 0 ? line.move(to: p) : line.addLine(to: p)
                    }
                    ctx.stroke(line, with: .color(Palette.lane(ch, total: count)), lineWidth: count > 8 ? 0.95 : 1.1)
                    // 右侧 RMS 条：对数刻度到 1000 µV，超过放松线变琥珀色
                    let r = band.rms[ch], frac = min(1, log10(1 + r / 10) / log10(101))
                    let track = CGRect(x: size.width - meterW + 4, y: midY - barH * 0.5, width: meterW - 30, height: barH)
                    ctx.fill(Path(roundedRect: track, cornerRadius: barH * 0.5), with: .color(Palette.line))
                    ctx.fill(Path(roundedRect: CGRect(x: track.minX, y: track.minY, width: track.width * CGFloat(frac), height: barH), cornerRadius: barH * 0.5),
                             with: .color(r < restMicrovolt ? Palette.teal : Palette.amber))
                    ctx.draw(Text("\(Int(r))").font(.system(size: fontSize, design: .rounded).monospacedDigit()).foregroundColor(Palette.dim),
                             at: CGPoint(x: size.width - 12, y: midY))
                    if ch < count - 1 {
                        ctx.fill(Path(CGRect(x: labelW, y: rowH * CGFloat(ch + 1), width: waveW, height: 0.5)), with: .color(Palette.line))
                    }
                }
            }
        }
        .padding(.vertical, 10).padding(.horizontal, 8)
        .background(Palette.card, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
        .overlay(alignment: .topTrailing) {
            Text("RMS µV").font(.system(size: 9, weight: .semibold)).foregroundStyle(Palette.dim).padding(.trailing, 14).padding(.top, 2)
        }
    }
}

struct GestureBar: View {
    @EnvironmentObject var gestures: Gestures
    @Binding var show: Bool
    var body: some View {
        Button { show = true } label: {
            HStack(spacing: 14) {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 8) {
                        Text(gestureNames[gestures.current]).font(.system(size: 30, weight: .bold, design: .rounded))
                            .contentTransition(.numericText())
                        Text("模拟").font(.caption2.weight(.bold)).foregroundStyle(Palette.amber)
                            .padding(.horizontal, 6).padding(.vertical, 2).background(Palette.amber.opacity(0.15), in: Capsule())
                    }
                    Text(gestureHints[gestures.current]).font(.footnote).foregroundStyle(Palette.dim)
                }
                Spacer()
                ConfidenceRing(value: gestures.probs[gestures.current], color: Palette.teal).frame(width: 52, height: 52)
                Image(systemName: "chevron.up").font(.footnote.weight(.bold)).foregroundStyle(Palette.dim)
            }
            .padding(16)
            .background(Palette.card, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
        }
        .buttonStyle(.plain)
        .animation(.snappy, value: gestures.current)
    }
}

struct ConfidenceRing: View {
    var value: Double
    var color: Color
    var label: String?
    var body: some View {
        ZStack {
            Circle().stroke(Palette.line, lineWidth: 5)
            Circle().trim(from: 0, to: value).stroke(color, style: StrokeStyle(lineWidth: 5, lineCap: .round))
                .rotationEffect(.degrees(-90)).animation(.easeOut(duration: 0.3), value: value)
            Text(label ?? String(format: "%.2f", value).replacingOccurrences(of: "0.", with: "."))
                .font(.system(size: 13, weight: .semibold, design: .rounded).monospacedDigit())
        }
    }
}

struct PendingBanner: View {
    let state: WatchState
    var body: some View {
        TimelineView(.periodic(from: .now, by: 1)) { ctx in
            let left = max(0, Int((state.deadline ?? ctx.date).timeIntervalSince(ctx.date).rounded(.up)))
            HStack(spacing: 10) {
                Image(systemName: "hand.raised.fingers.spread").foregroundStyle(Palette.amber)
                VStack(alignment: .leading, spacing: 1) {
                    Text("AI 待确认 · \(state.pendingCategory ?? "")").font(.subheadline.weight(.semibold))
                    Text("食指同意 · 中指拒绝").font(.caption).foregroundStyle(Palette.dim)
                }
                Spacer()
                Text("\(left)s").font(.system(.title3, design: .rounded).monospacedDigit().weight(.bold)).foregroundStyle(Palette.amber)
            }
            .padding(12)
            .background(Palette.amber.opacity(0.12), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        }
        .transition(.move(edge: .top).combined(with: .opacity))
    }
}

// MARK: 点开的附加视图：六类概率条 + 模拟

struct DetailSheet: View {
    @EnvironmentObject var gestures: Gestures
    @EnvironmentObject var band: Band
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    Text("六类手势").font(.system(.title2, design: .rounded).weight(.bold))
                    Spacer()
                    Text("模拟").font(.caption.weight(.bold)).foregroundStyle(Palette.amber)
                }
                ForEach(gestureNames.indices, id: \.self) { i in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(gestureNames[i]).font(.subheadline.weight(.semibold))
                            Text(gestureHints[i]).font(.caption).foregroundStyle(Palette.dim)
                            Spacer()
                            Text("\(Int((gestures.probs[i] * 100).rounded()))%").font(.system(.subheadline, design: .rounded).monospacedDigit())
                        }
                        GeometryReader { g in
                            ZStack(alignment: .leading) {
                                Capsule().fill(Palette.line)
                                Capsule().fill(i == gestures.current ? Palette.teal : Palette.cyan.opacity(0.5))
                                    .frame(width: max(6, g.size.width * gestures.probs[i]))
                            }
                        }.frame(height: 8)
                    }
                }
                .animation(.easeOut(duration: 0.25), value: gestures.probs)

                Text("模拟手势").font(.headline).padding(.top, 4)
                LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 3), spacing: 10) {
                    ForEach(gestureNames.indices, id: \.self) { i in
                        Button(gestureNames[i]) { gestures.simulate(i) }.buttonStyle(Pill(color: Palette.teal))
                    }
                }

                Text("AI 确认（模拟）").font(.headline).padding(.top, 4)
                if gestures.state.isPending {
                    HStack(spacing: 10) {
                        Button("食指碰拇指 · 同意") { gestures.decide(true) }.buttonStyle(Pill(color: Palette.teal))
                        Button("中指碰拇指 · 拒绝") { gestures.decide(false) }.buttonStyle(Pill(color: Palette.coral))
                    }
                } else {
                    Button("来一条待确认") { gestures.simulatePending() }.buttonStyle(Pill(color: Palette.amber))
                    if let r = gestures.state.result { Text("上一条：\(r)").font(.caption).foregroundStyle(Palette.dim) }
                }

                Text("手势模型还没移植到手机，这里的手势和确认是模拟的。" + (band.source.isEmpty
                     ? "波形、RMS 和放松判定来自手环实时数据（v12_dsp / c08b_dsp 滤波）。"
                     : "波形来自\(band.source)数据，不是人体肌电；滤波和 RMS 的算法与真实设备相同。"))
                    .font(.caption).foregroundStyle(Palette.dim).padding(.top, 6)
            }
            .padding(20)
        }
        .background(Palette.bg)
    }
}

struct Pill: ButtonStyle {
    var color: Color
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(.subheadline.weight(.semibold)).foregroundStyle(color)
            .frame(maxWidth: .infinity).padding(.vertical, 11)
            .background(color.opacity(configuration.isPressed ? 0.28 : 0.14), in: Capsule())
            .scaleEffect(configuration.isPressed ? 0.97 : 1)
    }
}
