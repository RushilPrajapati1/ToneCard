import SwiftUI

struct RootView: View {
    var body: some View {
        TabView {
            MoodView()
                .tabItem {
                    Label("Atlas", systemImage: "circle.grid.cross.fill")
                }
            LookupView()
                .tabItem {
                    Label("Lookup", systemImage: "magnifyingglass")
                }
        }
    }
}

#Preview {
    RootView()
        .environmentObject(AppConfig.shared)
}
