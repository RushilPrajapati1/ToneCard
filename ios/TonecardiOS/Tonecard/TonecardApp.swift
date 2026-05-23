import SwiftUI

@main
struct TonecardApp: App {
    @StateObject private var config = AppConfig.shared

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(config)
                .tint(Palette.accent)
        }
    }
}
