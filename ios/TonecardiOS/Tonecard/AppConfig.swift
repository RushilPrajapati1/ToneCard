import Foundation
import Combine

/// Holds the base URL of the Flask backend. On the iOS Simulator, `localhost`
/// resolves to the Mac running Flask, so the default just works. On a physical
/// iPhone, switch this (in Settings) to your Mac's LAN IP, e.g.
/// `http://192.168.1.42:5050`, and make sure Flask binds to 0.0.0.0.
final class AppConfig: ObservableObject {
    static let shared = AppConfig()

    static let defaultBaseURL = "http://localhost:5050"
    private static let key = "tonecard.baseURL"

    @Published var baseURLString: String {
        didSet { UserDefaults.standard.set(baseURLString, forKey: Self.key) }
    }

    private init() {
        baseURLString = UserDefaults.standard.string(forKey: Self.key) ?? Self.defaultBaseURL
    }

    var baseURL: URL? {
        URL(string: baseURLString.trimmingCharacters(in: .whitespacesAndNewlines))
    }

    func resetToDefault() {
        baseURLString = Self.defaultBaseURL
    }
}
