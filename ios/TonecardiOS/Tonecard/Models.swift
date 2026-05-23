import Foundation

// MARK: - Mood plane points

struct MoodPoint: Codable, Identifiable, Hashable {
    let id: String
    let name: String
    let artists: [String]
    let valence: Double
    let energy: Double
}

struct SeedResponse: Codable {
    let points: [MoodPoint]
    let genre: String?   // present only for /api/genre/seed
}

// MARK: - Tracks

struct TrackFeatures: Codable, Hashable {
    let valence: Double?
    let energy: Double?
    let tempo: Double?
    let danceability: Double?
}

struct Track: Codable, Identifiable, Hashable {
    let id: String
    let name: String
    let artists: [String]
    let album: String?
    let image: String?
    let url: String?
    let preview_url: String?
    let popularity: Int?
    let features: TrackFeatures?

    var artistText: String { artists.joined(separator: ", ") }
    var imageURL: URL? { image.flatMap { URL(string: $0) } }
    var previewURL: URL? { preview_url.flatMap { URL(string: $0) } }
    var openURL: URL? { url.flatMap { URL(string: $0) } }
}

struct MoodSearchResponse: Codable {
    struct Target: Codable { let valence: Double; let energy: Double }
    let target: Target?
    let recommendations: [Track]
    let candidate_count: Int?
    let feature_coverage: Int?
}

struct SearchResponse: Codable {
    let track: Track
    let genre: String?
    let similar: [Track]
    let pool_points: [MoodPoint]
    let candidate_count: Int?
}

// MARK: - Artists

struct Artist: Codable, Identifiable, Hashable {
    let id: String
    let name: String
    let genres: [String]
    let popularity: Int?
    let followers: Int?
    let image: String?
    let url: String?

    var imageURL: URL? { image.flatMap { URL(string: $0) } }
    var openURL: URL? { url.flatMap { URL(string: $0) } }
}

struct ArtistResponse: Codable {
    let artist: Artist
    let tracks: [Track]
    let points: [MoodPoint]
}

struct TrendingResponse: Codable {
    let artists: [Artist]
}

// MARK: - Errors

struct APIErrorBody: Codable {
    let error: String
}
