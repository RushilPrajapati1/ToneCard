import SwiftUI

/// Feature chips shown under a track (valence / energy / tempo).
struct FeatureChips: View {
    let features: TrackFeatures

    var body: some View {
        HStack(spacing: 6) {
            if let v = features.valence {
                Text("V \(Int((v * 100).rounded()))").modifier(ChipText())
            }
            if let e = features.energy {
                Text("E \(Int((e * 100).rounded()))").modifier(ChipText())
            }
            if let t = features.tempo {
                Text("\(Int(t.rounded())) BPM").modifier(ChipText())
            }
        }
    }
}

/// A pill button used for genre filters and mood presets.
struct PillButton: View {
    let title: String
    let selected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 13, weight: .medium, design: .monospaced))
                .foregroundStyle(selected ? Palette.accent : Palette.muted)
                .padding(.horizontal, 12)
                .padding(.vertical, 7)
                .background(selected ? Palette.accentSoft : Palette.surface, in: Capsule())
                .overlay(
                    Capsule().stroke(selected ? Palette.accent : Palette.line, lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
    }
}

/// Inline error banner with a retry affordance.
struct ErrorBanner: View {
    let message: String
    var retry: (() -> Void)?

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
            Text(message)
                .font(.system(size: 13))
                .foregroundStyle(Palette.ink)
                .fixedSize(horizontal: false, vertical: true)
            Spacer()
            if let retry {
                Button("Retry", action: retry)
                    .font(.system(size: 13, weight: .semibold))
                    .tint(Palette.accent)
            }
        }
        .padding(12)
        .background(Palette.surface, in: RoundedRectangle(cornerRadius: 12))
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Palette.line))
    }
}

/// Section header in the small-caps mono style used across the UI.
struct SectionLabel: View {
    let text: String
    var body: some View {
        Text(text.uppercased())
            .font(.system(size: 11, weight: .semibold, design: .monospaced))
            .tracking(1.5)
            .foregroundStyle(Palette.muted)
    }
}

/// Placeholder rows shown while results load.
struct SkeletonList: View {
    var rows: Int = 6
    @State private var pulse = false

    var body: some View {
        VStack(spacing: 14) {
            ForEach(0..<rows, id: \.self) { _ in
                HStack(spacing: 12) {
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Palette.line)
                        .frame(width: 52, height: 52)
                    VStack(alignment: .leading, spacing: 6) {
                        RoundedRectangle(cornerRadius: 4).fill(Palette.line).frame(width: 160, height: 12)
                        RoundedRectangle(cornerRadius: 4).fill(Palette.line).frame(width: 100, height: 10)
                    }
                    Spacer()
                }
            }
        }
        .opacity(pulse ? 0.45 : 1.0)
        .animation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true), value: pulse)
        .onAppear { pulse = true }
    }
}

/// Shared gear button that opens Settings.
@ToolbarContentBuilder
func settingsToolbar(showSettings: Binding<Bool>) -> some ToolbarContent {
    ToolbarItem(placement: .topBarTrailing) {
        Button {
            showSettings.wrappedValue = true
        } label: {
            Image(systemName: "gearshape")
        }
        .accessibilityLabel("Settings")
    }
}
