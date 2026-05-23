# Tonecard — iOS app

A native **SwiftUI** client for the Tonecard Flask backend. It reuses the
existing Python API as-is (no backend changes) and reimplements the two web
tabs natively:

- **Atlas** — interactive valence × energy plane (drag/tap the pin → Search),
  genre filter chips, mood presets, and a results list with inline 30-second
  preview playback.
- **Lookup** — Track or Artist search. Track mode shows the match + a
  read-only mood plane + similar tracks. Artist mode shows an artist card
  (avatar, genres, popularity, followers) + their tracks scattered on the plane.
  The empty state lists trending artists (tap to open).

The app is a *client* — it does not run Python. Your Flask backend
(`app.py`, port 5050) must be running, and the app points at it over HTTP.

## Requirements

- Xcode 16+ (built/tested with Xcode 26.5, Swift 5 language mode)
- iOS 17.0+ deployment target

## Run it (Simulator — the default)

1. Start the backend on your Mac:
   ```bash
   cd "/Users/rushi/Spotify Search APP"
   lsof -ti :5050 | xargs kill -9 2>/dev/null; ./venv/bin/python app.py
   ```
2. Open `ios/TonecardiOS/TonecardiOS.xcodeproj` in Xcode.
3. Pick any iOS Simulator and press ⌘R.

The Simulator shares your Mac's network, so the default backend URL
`http://localhost:5050` just works — no configuration needed.

### Command line

```bash
cd "ios/TonecardiOS"
xcodebuild -scheme Tonecard -sdk iphonesimulator \
  -destination 'id=<simulator-udid>' build
# then:  xcrun simctl install booted <DerivedData>/.../Tonecard.app
#        xcrun simctl launch booted com.tonecard.app
```

## Run it on a physical iPhone (free Apple ID)

`localhost` won't reach your Mac from a real device, and Flask currently binds
to `127.0.0.1` only. So:

1. Make Flask listen on the LAN. In `app.py`, change the last line to
   `app.run(host="0.0.0.0", port=5050, debug=False)` (or run a tunnel).
2. Find your Mac's LAN IP: `ipconfig getifaddr en0` (e.g. `192.168.1.42`).
3. In the app, tap the ⚙️ (Settings) and set the backend URL to
   `http://192.168.1.42:5050`, then **Test connection** → **Save**.
4. In Xcode, select your iPhone, set a Signing Team (your free Apple ID under
   *Signing & Capabilities*), and press ⌘R. Free-account builds re-sign every
   7 days.

> Cleartext HTTP to the Mac is allowed via an App Transport Security exception
> in `Info.plist` (`NSAllowsArbitraryLoads`). That's fine for a personal/dev
> build; tighten it before any App Store submission.

## Project layout

```
ios/TonecardiOS/
  TonecardiOS.xcodeproj/        # file-system-synchronized — drop new .swift
  Info.plist                    #   files into Tonecard/ and they're picked up
  Tonecard/
    TonecardApp.swift           # @main App entry
    AppConfig.swift             # backend URL (UserDefaults-backed)
    APIClient.swift             # async wrapper over the Flask JSON API
    Models.swift                # Codable models (match analyze.py shapes)
    PreviewPlayer.swift         # single AVPlayer, one preview at a time
    Theme.swift                 # color palette mirrored from the web CSS vars
    Assets.xcassets/            # AccentColor
    Views/
      RootView.swift            # TabView (Atlas / Lookup)
      MoodView.swift            # Atlas tab + view model
      MoodPlaneView.swift       # interactive valence×energy Canvas
      LookupView.swift          # Track/Artist search + trending + view model
      ArtistCardView.swift      # artist profile card
      TrackRowView.swift        # track row + ▶ preview button
      Components.swift          # chips, pills, skeleton, error banner
      SettingsView.swift        # backend URL editor + connection test
```

## Notes & parity

- Dark/light follows the iOS system appearance (the web app's manual toggle
  isn't needed). Colors are mirrored from the web CSS variables.
- The mood plane uses the same axis orientation as the web app:
  x = valence (Heavy → Bright), y = energy (Still → Charged).
- **Not yet ported:** the audio-file upload/analyze feature
  (`/api/upload/analyze`). The backend endpoint still exists; the iOS UI for
  picking a file and POSTing it is a follow-up.
```
