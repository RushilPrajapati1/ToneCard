import SwiftUI

/// Interactive valence × energy plane.
///   x: valence  (0 = Heavy / left, 1 = Bright / right)
///   y: energy   (1 = Charged / top, 0 = Still / bottom)
/// Dim dots are the seed pool; the accent pin is the current target.
/// Drag or tap anywhere to move the pin; `onCommit` fires when the drag ends.
struct MoodPlaneView: View {
    let seeds: [MoodPoint]
    @Binding var valence: Double
    @Binding var energy: Double
    var interactive: Bool = true
    var targetLabel: String? = nil
    var onCommit: () -> Void = {}

    var body: some View {
        GeometryReader { geo in
            let size = min(geo.size.width, geo.size.height)
            ZStack {
                RoundedRectangle(cornerRadius: 16)
                    .fill(Palette.surface)
                    .overlay(RoundedRectangle(cornerRadius: 16).stroke(Palette.line))

                Canvas { ctx, canvasSize in
                    // Center cross-hair grid.
                    var grid = Path()
                    grid.move(to: CGPoint(x: canvasSize.width / 2, y: 0))
                    grid.addLine(to: CGPoint(x: canvasSize.width / 2, y: canvasSize.height))
                    grid.move(to: CGPoint(x: 0, y: canvasSize.height / 2))
                    grid.addLine(to: CGPoint(x: canvasSize.width, y: canvasSize.height / 2))
                    ctx.stroke(grid, with: .color(Palette.line),
                               style: StrokeStyle(lineWidth: 1, dash: [4, 5]))

                    // Seed-pool dots.
                    for s in seeds {
                        let x = s.valence * canvasSize.width
                        let y = (1 - s.energy) * canvasSize.height
                        let r: CGFloat = 3
                        let rect = CGRect(x: x - r, y: y - r, width: r * 2, height: r * 2)
                        ctx.fill(Path(ellipseIn: rect), with: .color(Palette.accent.opacity(0.28)))
                    }
                }
                .padding(10)

                axisLabels(size: size)

                // Target pin.
                let px = valence * size
                let py = (1 - energy) * size
                ZStack {
                    Circle().fill(Palette.accent.opacity(0.18)).frame(width: 34, height: 34)
                    Circle().fill(Palette.accent).frame(width: 16, height: 16)
                        .overlay(Circle().stroke(Palette.surface, lineWidth: 3))
                }
                .position(x: px.clamped(to: 0...size), y: py.clamped(to: 0...size))
                .shadow(color: .black.opacity(0.15), radius: 3, y: 1)

                if let label = targetLabel {
                    Text(label)
                        .font(.system(size: 11, weight: .medium, design: .monospaced))
                        .padding(.horizontal, 6).padding(.vertical, 2)
                        .background(Palette.surface, in: Capsule())
                        .overlay(Capsule().stroke(Palette.line))
                        .position(x: px.clamped(to: 0...size),
                                  y: (py - 26).clamped(to: 0...size))
                }
            }
            .frame(width: size, height: size)
            .frame(maxWidth: .infinity)
            .contentShape(Rectangle())
            .gesture(dragGesture(size: size), including: interactive ? .all : .subviews)
        }
        .aspectRatio(1, contentMode: .fit)
        .accessibilityElement()
        .accessibilityLabel("Mood plane")
        .accessibilityValue("Valence \(Int((valence * 100).rounded())), energy \(Int((energy * 100).rounded()))")
        .accessibilityAdjustableAction { direction in
            guard interactive else { return }
            switch direction {
            case .increment: valence = (valence + 0.05).clamped(to: 0...1)
            case .decrement: valence = (valence - 0.05).clamped(to: 0...1)
            default: break
            }
            onCommit()
        }
    }

    private func dragGesture(size: CGFloat) -> some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { value in
                guard interactive, size > 0 else { return }
                valence = (value.location.x / size).clamped(to: 0...1)
                energy = (1 - value.location.y / size).clamped(to: 0...1)
            }
            .onEnded { _ in
                guard interactive else { return }
                onCommit()
            }
    }

    private func axisLabels(size: CGFloat) -> some View {
        ZStack {
            Text("↑ Charged").modifier(AxisLabel())
                .position(x: size / 2, y: 16)
            Text("↓ Still").modifier(AxisLabel())
                .position(x: size / 2, y: size - 16)
            Text("Heavy").modifier(AxisLabel())
                .rotationEffect(.degrees(-90))
                .position(x: 16, y: size / 2)
            Text("Bright").modifier(AxisLabel())
                .rotationEffect(.degrees(90))
                .position(x: size - 16, y: size / 2)
        }
        .frame(width: size, height: size)
    }
}

private struct AxisLabel: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(.system(size: 10, weight: .medium, design: .monospaced))
            .foregroundStyle(Palette.muted)
    }
}

extension Comparable {
    func clamped(to range: ClosedRange<Self>) -> Self {
        min(max(self, range.lowerBound), range.upperBound)
    }
}
