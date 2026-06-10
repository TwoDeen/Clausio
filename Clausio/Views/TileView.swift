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
  let mergesLeft: Bool
  let mergesRight: Bool
  let isBold: Bool = false
  let action: () -> Void
  
  @Environment(\.verticalSizeClass) var verticalSizeClass
  
  var body: some View {
    Button(action: action) {
      if verticalSizeClass == .compact {
        // 💡 FIXED: Bypasses the .aspectRatio wrapper completely so cells safely morph into wide rectangles
        tileContent
      } else {
        tileContent
          .aspectRatio(1.0, contentMode: .fit)
      }
    }
    .buttonStyle(.plain)
    .frame(maxWidth: .infinity, maxHeight: .infinity) // Forces the structural wrapper to scale out flush
  }
  
  private var tileContent: some View {
    ZStack(alignment: .topTrailing) {
      GeometryReader { geometry in
        VStack {
          Spacer()
          Text(Self.balancedJapaneseText(for: tile.text, baseSize: min(geometry.size.width, geometry.size.height) * 0.24, isSolved: tile.isSolved))
            .minimumScaleFactor(0.35)
            .multilineTextAlignment(.center)
            .foregroundColor(tile.isSolved ? .black : .primary)
            .padding(.horizontal, 4)
          Spacer()
        }
        .frame(width: geometry.size.width, height: geometry.size.height)
        .background(
          tileShape
            .fill(tile.isSolved ? accentColor : Color.gray.opacity(0.2))
            .padding(.leading, mergesLeft ? -1.5 : 0)
            .padding(.trailing, mergesRight ? -1.5 : 0)
        )
        .overlay(
          tileShape
            .stroke(isSelected ? Color.blue : Color.clear, lineWidth: 3)
            .padding(.leading, mergesLeft ? -1.5 : 0)
            .padding(.trailing, mergesRight ? -1.5 : 0)
        )
      }
      
      if isSelected {
        Image(systemName: "checkmark.circle.fill")
          .font(.caption)
          .foregroundColor(.blue)
          .padding(4)
      }
    }
  }
  
  private var tileShape: UnevenRoundedRectangle {
    let leftRadius: CGFloat = mergesLeft ? 0 : (isAssistModeOn ? 2 : 8)
    let rightRadius: CGFloat = mergesRight ? 0 : (isAssistModeOn ? 2 : 8)
    
    return UnevenRoundedRectangle(
      topLeadingRadius: leftRadius,
      bottomLeadingRadius: leftRadius,
      bottomTrailingRadius: rightRadius,
      topTrailingRadius: rightRadius
    )
  }
  
  static func balancedJapaneseText(for text: String, baseSize: CGFloat, isSolved: Bool) -> AttributedString {
    var combinedString = AttributedString()
    
    let kanjiScaleFactor: CGFloat = 1.12
    let kanjiBaselineOffset: CGFloat = -0.5
    let kanjiStrokeThickness: Double = -2.2
    
    for char in text {
      var singleCharString = AttributedString(String(char))
      
      let isKanji = char.unicodeScalars.contains { scalar in
        return (0x4E00...0x9FFF).contains(scalar.value) ||
        (0x3400...0x4DBF).contains(scalar.value)
      }
      
      if isKanji {
        singleCharString.font = .custom("japaneseSVGFont-Bold", size: baseSize * kanjiScaleFactor)
        singleCharString.baselineOffset = kanjiBaselineOffset
        
#if os(iOS)
        singleCharString.uiKit.strokeWidth = kanjiStrokeThickness
        singleCharString.uiKit.strokeColor = isSolved ? .black : .label
#elseif os(macOS)
        singleCharString.appKit.strokeWidth = kanjiStrokeThickness
        singleCharString.appKit.strokeColor = isSolved ? .black : .textColor
#endif
      } else {
        singleCharString.font = .custom("japaneseSVGFont", size: baseSize)
      }
      combinedString.append(singleCharString)
    }
    return combinedString
  }
}

// MARK: - Global Font Definitions Extension
extension Font {
  static func customJp(_ style: JpStyle, size: CGFloat) -> Font {
    return .custom(style.rawValue, size: size)
  }
  
  enum JpStyle: String {
    case regular = "japaneseSVGFont"
    case bold = "japaneseSVGFont-Bold"
  }
}
