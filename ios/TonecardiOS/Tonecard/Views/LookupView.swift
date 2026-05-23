import SwiftUI

@MainActor
final class LookupModel: ObservableObject {
    enum Mode: String, CaseIterable, Identifiable {
        case track = "Track"
        case artist = "Artist"
        var id: String { rawValue }
    }

    @Published var mode: Mode = .track
    @Published var query: String = ""
    @Published var loading = false
    @Published var errorMessage: String?
    @Published var searchResult: SearchResponse?
    @Published var artistResult: ArtistResponse?
    @Published var trending: [Artist] = []

    private let api = APIClient()

    func run() async {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { return }
        loading = true
        errorMessage = nil
        defer { loading = false }
        do {
            switch mode {
            case .track:
                searchResult = try await api.search(q)
                artistResult = nil
            case .artist:
                artistResult = try await api.artist(q)
                searchResult = nil
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func clearResults() {
        searchResult = nil
        artistResult = nil
        errorMessage = nil
    }

    func loadTrending() async {
        guard trending.isEmpty else { return }
        do { trending = try await api.trending() } catch { /* silent: it's a nicety */ }
    }

    func openArtist(_ name: String) async {
        query = name
        mode = .artist
        await run()
    }
}

struct LookupView: View {
    @StateObject private var model = LookupModel()
    @State private var showSettings = false
    @FocusState private var searchFocused: Bool

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    modePicker
                    searchField

                    if let error = model.errorMessage {
                        ErrorBanner(message: error) { Task { await model.run() } }
                    }

                    content
                }
                .padding(16)
            }
            .background(Palette.bg)
            .navigationTitle("Lookup")
            .toolbar { settingsToolbar(showSettings: $showSettings) }
            .sheet(isPresented: $showSettings) { SettingsView() }
        }
        .task { await model.loadTrending() }
    }

    private var modePicker: some View {
        Picker("Mode", selection: $model.mode) {
            ForEach(LookupModel.Mode.allCases) { mode in
                Text(mode.rawValue).tag(mode)
            }
        }
        .pickerStyle(.segmented)
        .onChange(of: model.mode) { _, _ in model.clearResults() }
    }

    private var searchField: some View {
        HStack(spacing: 8) {
            Image(systemName: "magnifyingglass").foregroundStyle(Palette.muted)
            TextField(model.mode == .track ? "Song name…" : "Artist name…", text: $model.query)
                .textInputAutocapitalization(.words)
                .autocorrectionDisabled()
                .focused($searchFocused)
                .submitLabel(.search)
                .onSubmit { Task { await model.run() } }
            if !model.query.isEmpty {
                Button {
                    model.query = ""
                    model.clearResults()
                } label: {
                    Image(systemName: "xmark.circle.fill").foregroundStyle(Palette.muted)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 11)
        .background(Palette.surface, in: RoundedRectangle(cornerRadius: 12))
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Palette.line))
    }

    @ViewBuilder
    private var content: some View {
        if model.loading {
            SkeletonList()
        } else if let result = model.searchResult {
            trackResult(result)
        } else if let result = model.artistResult {
            artistResult(result)
        } else {
            trendingSection
        }
    }

    // MARK: Track result

    private func trackResult(_ result: SearchResponse) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    SectionLabel(text: "Match")
                    if let genre = result.genre {
                        Text("· \(genre)")
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(Palette.muted)
                    }
                }
                TrackRowView(track: result.track)
            }

            if let features = result.track.features,
               let v = features.valence, let e = features.energy {
                MoodPlaneView(
                    seeds: result.pool_points,
                    valence: .constant(v),
                    energy: .constant(e),
                    interactive: false,
                    targetLabel: "this"
                )
            }

            if !result.similar.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    SectionLabel(text: "Similar mood")
                    ForEach(result.similar) { track in
                        TrackRowView(track: track)
                        if track.id != result.similar.last?.id {
                            Divider().overlay(Palette.line)
                        }
                    }
                }
            }
        }
    }

    // MARK: Artist result

    private func artistResult(_ result: ArtistResponse) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            ArtistCardView(artist: result.artist)

            if !result.points.isEmpty {
                MoodPlaneView(
                    seeds: result.points,
                    valence: .constant(0.5),
                    energy: .constant(0.5),
                    interactive: false
                )
            }

            if !result.tracks.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    SectionLabel(text: "Top tracks")
                    ForEach(result.tracks) { track in
                        TrackRowView(track: track)
                        if track.id != result.tracks.last?.id {
                            Divider().overlay(Palette.line)
                        }
                    }
                }
            }
        }
    }

    // MARK: Trending (empty state)

    @ViewBuilder
    private var trendingSection: some View {
        if !model.trending.isEmpty {
            VStack(alignment: .leading, spacing: 10) {
                SectionLabel(text: "Trending artists")
                ForEach(model.trending) { artist in
                    Button {
                        Task { await model.openArtist(artist.name) }
                    } label: {
                        HStack(spacing: 12) {
                            AsyncImage(url: artist.imageURL) { phase in
                                if case .success(let image) = phase {
                                    image.resizable().aspectRatio(contentMode: .fill)
                                } else {
                                    Circle().fill(Palette.line)
                                }
                            }
                            .frame(width: 44, height: 44)
                            .clipShape(Circle())

                            VStack(alignment: .leading, spacing: 2) {
                                Text(artist.name)
                                    .font(.system(size: 15, weight: .semibold))
                                    .foregroundStyle(Palette.ink)
                                Text(artist.genres.prefix(2).joined(separator: " · "))
                                    .font(.system(size: 12, design: .monospaced))
                                    .foregroundStyle(Palette.muted)
                                    .lineLimit(1)
                            }
                            Spacer()
                            Image(systemName: "chevron.right").foregroundStyle(Palette.muted)
                        }
                        .padding(.vertical, 4)
                    }
                    .buttonStyle(.plain)
                    Divider().overlay(Palette.line)
                }
            }
        } else {
            VStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 32))
                    .foregroundStyle(Palette.muted)
                Text("Search a song or artist to begin.")
                    .font(.system(size: 14))
                    .foregroundStyle(Palette.muted)
            }
            .frame(maxWidth: .infinity)
            .padding(.top, 40)
        }
    }
}
