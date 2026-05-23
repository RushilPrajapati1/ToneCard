import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var config: AppConfig
    @Environment(\.dismiss) private var dismiss
    @State private var draft: String = ""
    @State private var testState: TestState = .idle

    enum TestState: Equatable {
        case idle, testing, ok, failed(String)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("http://localhost:5050", text: $draft)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                        .font(.system(.body, design: .monospaced))
                } header: {
                    Text("Backend URL")
                } footer: {
                    Text("On the Simulator, localhost reaches Flask on your Mac. On a physical iPhone, use your Mac's LAN IP (e.g. http://192.168.1.42:5050) and run Flask with host=\"0.0.0.0\".")
                }

                Section {
                    Button {
                        Task { await testConnection() }
                    } label: {
                        HStack {
                            Text("Test connection")
                            Spacer()
                            switch testState {
                            case .idle: EmptyView()
                            case .testing: ProgressView().controlSize(.small)
                            case .ok: Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                            case .failed: Image(systemName: "xmark.circle.fill").foregroundStyle(.red)
                            }
                        }
                    }
                    if case .failed(let msg) = testState {
                        Text(msg).font(.system(size: 12)).foregroundStyle(.red)
                    }
                    if case .ok = testState {
                        Text("Reached the backend.").font(.system(size: 12)).foregroundStyle(.green)
                    }
                }

                Section {
                    Button("Reset to default") {
                        draft = AppConfig.defaultBaseURL
                        testState = .idle
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Save") {
                        config.baseURLString = draft.trimmingCharacters(in: .whitespacesAndNewlines)
                        dismiss()
                    }
                    .fontWeight(.semibold)
                }
            }
            .onAppear { draft = config.baseURLString }
        }
    }

    private func testConnection() async {
        testState = .testing
        // Temporarily honor the draft URL for the test.
        let saved = config.baseURLString
        config.baseURLString = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        defer { config.baseURLString = saved }
        do {
            _ = try await APIClient().trending()
            testState = .ok
        } catch {
            testState = .failed(error.localizedDescription)
        }
    }
}
