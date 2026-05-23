import Foundation

enum APIClientError: LocalizedError {
    case badURL
    case server(String)
    case http(Int)
    case decoding(String)
    case offline

    var errorDescription: String? {
        switch self {
        case .badURL:        return "Invalid server URL. Check Settings."
        case .server(let m): return m
        case .http(let c):   return "Server returned HTTP \(c)."
        case .decoding(let m): return "Couldn't read the response. \(m)"
        case .offline:       return "Can't reach the backend. Is Flask running on \(AppConfig.shared.baseURLString)?"
        }
    }
}

/// Thin async wrapper over the Flask JSON API.
struct APIClient {
    var config: AppConfig = .shared

    private func makeURL(_ path: String, _ items: [URLQueryItem]) -> URL? {
        guard let base = config.baseURL,
              var comps = URLComponents(url: base, resolvingAgainstBaseURL: false) else {
            return nil
        }
        comps.path = path
        comps.queryItems = items.isEmpty ? nil : items
        return comps.url
    }

    private func get<T: Decodable>(_ path: String, query: [URLQueryItem] = [], as type: T.Type) async throws -> T {
        guard let url = makeURL(path, query) else { throw APIClientError.badURL }
        var req = URLRequest(url: url)
        req.timeoutInterval = 30
        req.setValue("application/json", forHTTPHeaderField: "Accept")

        let data: Data
        let resp: URLResponse
        do {
            (data, resp) = try await URLSession.shared.data(for: req)
        } catch let urlErr as URLError where urlErr.code == .cannotConnectToHost
            || urlErr.code == .cannotFindHost
            || urlErr.code == .timedOut
            || urlErr.code == .notConnectedToInternet {
            throw APIClientError.offline
        }

        guard let http = resp as? HTTPURLResponse else { throw APIClientError.http(-1) }
        guard (200..<300).contains(http.statusCode) else {
            if let body = try? JSONDecoder().decode(APIErrorBody.self, from: data) {
                throw APIClientError.server(body.error)
            }
            throw APIClientError.http(http.statusCode)
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw APIClientError.decoding(String(describing: error))
        }
    }

    private func q(_ name: String, _ value: String) -> URLQueryItem {
        URLQueryItem(name: name, value: value)
    }

    private func coord(_ d: Double) -> String { String(format: "%.4f", d) }

    // MARK: Endpoints

    func moodSeed(market: String = "US") async throws -> [MoodPoint] {
        try await get("/api/mood/seed", query: [q("market", market)], as: SeedResponse.self).points
    }

    func mood(valence: Double, energy: Double, count: Int = 12, market: String = "US") async throws -> MoodSearchResponse {
        try await get("/api/mood", query: [
            q("valence", coord(valence)), q("energy", coord(energy)),
            q("count", String(count)), q("market", market),
        ], as: MoodSearchResponse.self)
    }

    func genreSeed(genre: String, market: String = "US") async throws -> [MoodPoint] {
        try await get("/api/genre/seed", query: [q("genre", genre), q("market", market)], as: SeedResponse.self).points
    }

    func genre(genre: String, valence: Double, energy: Double, count: Int = 12, market: String = "US") async throws -> MoodSearchResponse {
        try await get("/api/genre", query: [
            q("genre", genre),
            q("valence", coord(valence)), q("energy", coord(energy)),
            q("count", String(count)), q("market", market),
        ], as: MoodSearchResponse.self)
    }

    func search(_ text: String, count: Int = 12, market: String = "US") async throws -> SearchResponse {
        try await get("/api/search", query: [
            q("q", text), q("count", String(count)), q("market", market),
        ], as: SearchResponse.self)
    }

    func artist(_ text: String, count: Int = 12, market: String = "US") async throws -> ArtistResponse {
        try await get("/api/artist", query: [
            q("q", text), q("count", String(count)), q("market", market),
        ], as: ArtistResponse.self)
    }

    func trending() async throws -> [Artist] {
        try await get("/api/artists/trending", as: TrendingResponse.self).artists
    }
}
