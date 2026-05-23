import SwiftUI

struct TrackRowView: View {
    let track: Track
    @ObservedObject private var player = PreviewPlayer.shared

    var body: some View {
        HStack(spacing: 12) {
            artwork

            VStack(alignment: .leading, spacing: 4) {
                Text(track.name)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(Palette.ink)
                    .lineLimit(1)
                Text(track.artistText)
                    .font(.system(size: 13))
                    .foregroundStyle(Palette.muted)
                    .lineLimit(1)
                if let features = track.features {
                    FeatureChips(features: features)
                }
            }

            Spacer(minLength: 8)

            if track.previewURL != nil {
                Button {
                    player.toggle(track)
                } label: {
                    Image(systemName: player.isCurrent(track) ? "pause.circle.fill" : "play.circle.fill")
                        .font(.system(size: 30))
                        .foregroundStyle(Palette.accent)
                        .symbolRenderingMode(.hierarchical)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(player.isCurrent(track) ? "Pause preview" : "Play preview")
            }

            if let open = track.openURL {
                Link(destination: open) {
                    Image(systemName: "arrow.up.forward.app")
                        .font(.system(size: 18))
                        .foregroundStyle(Palette.muted)
                }
                .accessibilityLabel("Open in Spotify")
            }
        }
        .padding(.vertical, 6)
    }

    private var artwork: some View {
        AsyncImage(url: track.imageURL) { phase in
            switch phase {
            case .success(let image):
                image.resizable().aspectRatio(contentMode: .fill)
            default:
                Rectangle()
                    .fill(Palette.line)
                    .overlay(
                        Image(systemName: "music.note")
                            .foregroundStyle(Palette.muted)
                    )
            }
        }
        .frame(width: 52, height: 52)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}
