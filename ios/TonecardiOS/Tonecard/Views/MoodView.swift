import SwiftUI

struct Genre: Identifiable, Hashable {
    let label: String
    let query: String?   // nil == "All moods"
    var id: String { label }
}

let GENRES: [Genre] = [
    .init(label: "All moods", query: nil),
    .init(label: "Pop", query: "pop"),
    .init(label: "Hip-Hop", query: "hip hop"),
    .init(label: "Rock", query: "rock"),
    .init(label: "R&B", query: "r&b"),
    .init(label: "Electronic", query: "electronic"),
    .init(label: "Jazz", query: "jazz"),
    .init(label: "Classical", query: "classical"),
    .init(label: "Latin", query: "latin"),
    .init(label: "Punjabi", query: "punjabi"),
    .init(label: "Metal", query: "metal"),
    .init(label: "Country", query: "country"),
    .init(label: "Indie", query: "indie"),
]

struct MoodPreset: Identifiable {
    let label: String
    let v: Double
    let e: Double
    var id: String { label }
}

let MOOD_PRESETS: [MoodPreset] = [
    .init(label: "Still + heavy", v: 0.25, e: 0.20),
    .init(label: "Still + bright", v: 0.75, e: 0.25),
    .init(label: "Wired + heavy", v: 0.20, e: 0.80),
    .init(label: "Wired + bright", v: 0.80, e: 0.85),
    .init(label: "Dead center", v: 0.50, e: 0.50),
]

@MainActor
final class MoodModel: ObservableObject {
    @Published var genreQuery: String? = nil
    @Published var valence: Double = 0.5
    @Published var energy: Double = 0.5
    @Published var seeds: [MoodPoint] = []
    @Published var results: [Track] = []
    @Published var loadingSeeds = false
    @Published var loadingResults = false
    @Published var errorMessage: String?
    @Published var hasSearched = false

    private let api = APIClient()

    func loadSeeds() async {
        loadingSeeds = true
        errorMessage = nil
        defer { loadingSeeds = false }
        do {
            if let g = genreQuery {
                seeds = try await api.genreSeed(genre: g)
            } else {
                seeds = try await api.moodSeed()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func selectGenre(_ g: String?) async {
        guard g != genreQuery else { return }
        genreQuery = g
        seeds = []
        await loadSeeds()
        if hasSearched { await search() }
    }

    func search() async {
        loadingResults = true
        errorMessage = nil
        hasSearched = true
        defer { loadingResults = false }
        do {
            let resp: MoodSearchResponse
            if let g = genreQuery {
                resp = try await api.genre(genre: g, valence: valence, energy: energy)
            } else {
                resp = try await api.mood(valence: valence, energy: energy)
            }
            results = resp.recommendations
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

struct MoodView: View {
    @StateObject private var model = MoodModel()
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    genreChips
                    plane
                    presets

                    if let error = model.errorMessage {
                        ErrorBanner(message: error) {
                            Task { await model.search() }
                        }
                    }

                    results
                }
                .padding(16)
            }
            .background(Palette.bg)
            .navigationTitle("Atlas")
            .toolbar { settingsToolbar(showSettings: $showSettings) }
            .sheet(isPresented: $showSettings) { SettingsView() }
        }
        .task {
            if model.seeds.isEmpty { await model.loadSeeds() }
        }
    }

    private var genreChips: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(GENRES) { genre in
                    PillButton(
                        title: genre.label,
                        selected: genre.query == model.genreQuery
                    ) {
                        Task { await model.selectGenre(genre.query) }
                    }
                }
            }
            .padding(.horizontal, 2)
        }
    }

    private var plane: some View {
        VStack(spacing: 10) {
            MoodPlaneView(
                seeds: model.seeds,
                valence: $model.valence,
                energy: $model.energy
            ) {
                Task { await model.search() }
            }

            HStack {
                if model.loadingSeeds {
                    HStack(spacing: 6) {
                        ProgressView().controlSize(.small)
                        Text("Building mood pool…")
                            .font(.system(size: 12, design: .monospaced))
                            .foregroundStyle(Palette.muted)
                    }
                } else {
                    Text("\(model.seeds.count) tracks · drag the pin, then Search")
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundStyle(Palette.muted)
                }
                Spacer()
                Button {
                    Task { await model.search() }
                } label: {
                    if model.loadingResults {
                        ProgressView().controlSize(.small)
                    } else {
                        Label("Search", systemImage: "scope")
                            .font(.system(size: 14, weight: .semibold))
                    }
                }
                .buttonStyle(.borderedProminent)
                .tint(Palette.accent)
                .disabled(model.loadingResults)
            }
        }
    }

    private var presets: some View {
        VStack(alignment: .leading, spacing: 8) {
            SectionLabel(text: "Presets")
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(MOOD_PRESETS) { preset in
                        PillButton(title: preset.label, selected: false) {
                            model.valence = preset.v
                            model.energy = preset.e
                            Task { await model.search() }
                        }
                    }
                }
                .padding(.horizontal, 2)
            }
        }
    }

    @ViewBuilder
    private var results: some View {
        if model.loadingResults && model.results.isEmpty {
            SkeletonList()
        } else if !model.results.isEmpty {
            VStack(alignment: .leading, spacing: 4) {
                SectionLabel(text: "Closest tracks")
                ForEach(model.results) { track in
                    TrackRowView(track: track)
                    if track.id != model.results.last?.id {
                        Divider().overlay(Palette.line)
                    }
                }
            }
        } else if model.hasSearched {
            Text("No tracks for that point. Try another genre or move the pin.")
                .font(.system(size: 13))
                .foregroundStyle(Palette.muted)
                .padding(.top, 8)
        }
    }
}
