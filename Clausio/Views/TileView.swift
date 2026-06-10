//
//  TileView.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 10/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI

// MARK: - Grid Tile Subview
struct TileView: View {
  let tile: Tile
  let isSelected: Bool
  let accentColor: Color
  let isAssistModeOn: Bool
  let isBold: Bool = false
  let action: () -> Void
  
  var body: some View {
    Button(action: action) {
      ZStack(alignment: .topTrailing) {
        // GeometryReader captures the container dimensions at runtime
        GeometryReader { geometry in
          VStack {
            Spacer()
            // Passes the dynamic tile width into the font balancing engine
            Text(balancedJapaneseText(for: tile.text, baseSize: geometry.size.width * 0.22))
              .minimumScaleFactor(0.35)
              .multilineTextAlignment(.center)
              .foregroundColor(tile.isSolved ? .black : .primary)
              .padding(.horizontal, 4)
            Spacer()
          }
          .frame(width: geometry.size.width, height: geometry.size.height)
        }
        .aspectRatio(1.0, contentMode: .fit)
        .background(
          RoundedRectangle(cornerRadius: isAssistModeOn ? 2 : 8)
            .fill(tile.isSolved ? accentColor : Color.gray.opacity(0.2))
        )
        .overlay(
          RoundedRectangle(cornerRadius: isAssistModeOn ? 2 : 8)
            .stroke(isSelected ? Color.blue : Color.clear, lineWidth: 3)
        )
        
        if isSelected {
          Image(systemName: "checkmark.circle.fill")
            .font(.caption)
            .foregroundColor(.blue)
            .padding(4)
        }
      }
    }
    //.disabled(tile.isSolved)
  }
  
  // Automatically splits text, boosts Kanji sizes, and thickens Kanji strokes to match heavy Kana
  private func balancedJapaneseText(for text: String, baseSize: CGFloat) -> AttributedString {
    var combinedString = AttributedString()
    
    // TWEAK THESE THREE VARIABLES TO PERFECTLY BALANCE YOUR VISUALS
    let kanjiScaleFactor: CGFloat = 1.12     // 🔽 Dropped from 1.35 to 1.12 to shrink the Kanji frame down
    let kanjiBaselineOffset: CGFloat = -0.5  // 🔼 Shifted closer to 0 since the character is smaller now
    let kanjiStrokeThickness: Double = -2.2  // 🎨 Kept rich and thick so it matches the Kana stroke weight
    
    for char in text {
      var singleCharString = AttributedString(String(char))
      
      // Check if character falls within standard Kanji Unicode ranges
      let isKanji = char.unicodeScalars.contains { scalar in
        return (0x4E00...0x9FFF).contains(scalar.value) ||
        (0x3400...0x4DBF).contains(scalar.value)
      }
      
      if isKanji {
        // 1. Force Kanji to use the BOLD asset variant to catch up to the naturally heavy Kana
        singleCharString.font = .custom("japaneseSVGFont-Bold", size: baseSize * kanjiScaleFactor)
        singleCharString.baselineOffset = kanjiBaselineOffset
        
        // 2. Inject negative stroke rendering to beef up the thin Kanji lines (Cross-Platform Safe)
#if os(iOS)
        singleCharString.uiKit.strokeWidth = kanjiStrokeThickness
        singleCharString.uiKit.strokeColor = tile.isSolved ? .black : .label
#elseif os(macOS)
        singleCharString.appKit.strokeWidth = kanjiStrokeThickness
        singleCharString.appKit.strokeColor = tile.isSolved ? .black : .textColor
#endif
        
      } else {
        // Keep Kana mapped to the Regular asset variant
        singleCharString.font = .custom("japaneseSVGFont", size: baseSize)
      }
      
      combinedString.append(singleCharString)
    }
    
    return combinedString
  }
}

extension Font {
  static func notoCcSans(_ style: NotoStyle, size: CGFloat) -> Font {
    return .custom(style.rawValue, size: size)
  }
  
  enum NotoStyle: String {
    case regular = "japaneseSVGFont"
    case bold = "japaneseSVGFont-Bold"
  }
}
