import Foundation
import AVFoundation
import Combine

/// Single shared audio element that plays 30-second previews one at a time —
/// mirrors the web app's single-<audio> behavior.
@MainActor
final class PreviewPlayer: ObservableObject {
    static let shared = PreviewPlayer()

    @Published private(set) var currentID: String?
    @Published private(set) var isPlaying = false

    private var player: AVPlayer?
    private var endObserver: NSObjectProtocol?

    private init() {}

    func isCurrent(_ track: Track) -> Bool {
        currentID == track.id && isPlaying
    }

    /// Play this track's preview, or pause it if it's the one already playing.
    func toggle(_ track: Track) {
        guard let url = track.previewURL else { return }
        if currentID == track.id, isPlaying {
            stop()
            return
        }
        stop()
        configureSession()

        let item = AVPlayerItem(url: url)
        let newPlayer = AVPlayer(playerItem: item)
        player = newPlayer
        currentID = track.id
        isPlaying = true

        endObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: item,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in self?.stop() }
        }

        newPlayer.play()
    }

    func stop() {
        player?.pause()
        player = nil
        isPlaying = false
        currentID = nil
        if let observer = endObserver {
            NotificationCenter.default.removeObserver(observer)
            endObserver = nil
        }
    }

    private func configureSession() {
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .default)
        try? session.setActive(true)
    }
}
