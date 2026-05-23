import SwiftUI

struct ArtistCardView: View {
    let artist: Artist

    var body: some View {
        VStack(spacing: 14) {
            HStack(spacing: 14) {
                avatar
                VStack(alignment: .leading, spacing: 6) {
                    Text(artist.name)
                        .font(.system(size: 20, weight: .bold))
                        .foregroundStyle(Palette.ink)
                        .lineLimit(2)
                    if !artist.genres.isEmpty {
                        Text(artist.genres.prefix(4).joined(separator: " · "))
                            .font(.system(size: 12, design: .monospaced))
                            .foregroundStyle(Palette.muted)
                            .lineLimit(2)
                    }
                    if let open = artist.openURL {
                        Link(destination: open) {
                            Label("Open in Spotify", systemImage: "arrow.up.forward.app")
                                .font(.system(size: 12, weight: .semibold))
                        }
                        .tint(Palette.accent)
                    }
                }
                Spacer(minLength: 0)
            }

            HStack(spacing: 12) {
                stat(value: "\(artist.popularity ?? 0)", label: "Popularity")
                stat(value: formatted(artist.followers ?? 0), label: "Followers")
            }
        }
        .padding(16)
        .background(Palette.surface, in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Palette.line))
    }

    private var avatar: some View {
        AsyncImage(url: artist.imageURL) { phase in
            switch phase {
            case .success(let image):
                image.resizable().aspectRatio(contentMode: .fill)
            default:
                Circle().fill(Palette.line).overlay(
                    Image(systemName: "person.fill").foregroundStyle(Palette.muted)
                )
            }
        }
        .frame(width: 84, height: 84)
        .clipShape(Circle())
        .overlay(Circle().stroke(Palette.line))
    }

    private func stat(value: String, label: String) -> some View {
        VStack(spacing: 2) {
            Text(value)
                .font(.system(size: 18, weight: .bold, design: .rounded))
                .foregroundStyle(Palette.ink)
            Text(label.uppercased())
                .font(.system(size: 10, weight: .medium, design: .monospaced))
                .tracking(1)
                .foregroundStyle(Palette.muted)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .background(Palette.accentSoft, in: RoundedRectangle(cornerRadius: 12))
    }

    private func formatted(_ n: Int) -> String {
        if n >= 1_000_000 {
            return String(format: "%.1fM", Double(n) / 1_000_000)
        } else if n >= 1_000 {
            return String(format: "%.0fK", Double(n) / 1_000)
        }
        return "\(n)"
    }
}
