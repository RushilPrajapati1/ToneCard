import SwiftUI
import UIKit

/// Color palette mirrored from the web app's CSS variables (light + dark).
enum Palette {
    static let bg         = Color(light: "F4F2EC", dark: "0B0E11")
    static let surface    = Color(light: "FFFFFF", dark: "1A2029")
    static let ink        = Color(light: "111418", dark: "ECEEF1")
    static let muted      = Color(light: "7A818A", dark: "6E747D")
    static let line       = Color(light: "D9D5CB", dark: "232A33")
    static let accent     = Color(light: "0F7F86", dark: "3FD3DC")
    static let accentSoft = Color(light: "D9EEEE", dark: "0F3033")
}

extension Color {
    /// A color that resolves differently in light vs dark mode.
    init(light: String, dark: String) {
        self = Color(UIColor { trait in
            trait.userInterfaceStyle == .dark ? UIColor(hex: dark) : UIColor(hex: light)
        })
    }
}

extension UIColor {
    convenience init(hex: String) {
        var s = hex.trimmingCharacters(in: .whitespaces)
        if s.hasPrefix("#") { s.removeFirst() }
        var value: UInt64 = 0
        Scanner(string: s).scanHexInt64(&value)
        let r = CGFloat((value & 0xFF0000) >> 16) / 255.0
        let g = CGFloat((value & 0x00FF00) >> 8) / 255.0
        let b = CGFloat(value & 0x0000FF) / 255.0
        self.init(red: r, green: g, blue: b, alpha: 1.0)
    }
}

/// Small monospaced "chip" used for feature labels (V / E / BPM).
struct ChipText: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(.system(size: 11, weight: .medium, design: .monospaced))
            .foregroundStyle(Palette.muted)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(Palette.accentSoft, in: Capsule())
    }
}
