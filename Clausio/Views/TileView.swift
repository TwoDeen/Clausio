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
  let useSquareAspectRatio: Bool
  let isBold: Bool = false
  let action: () -> Void
  
  private var endsWithParticle: Bool {
    let particles = ["を", "に", "が", "は", "と", "で", "へ", "の", "も", "か", "ね", "よ"]
    return particles.contains { tile.text.hasSuffix($0) }
  }
  
  // 🚀 THE FIX: A pure, unconstrained button that greedily fills all available space
  private var coreButton: some View {
    Button(action: action) {
      ZStack(alignment: .topTrailing) {
        
        // Forces the label to push out to the exact edges of the Button frame
        VStack(spacing: 0) {
          Spacer(minLength: 0)
          Text(Self.balancedJapaneseText(for: tile.text, baseSize: 15, isSolved: tile.isSolved))
            .lineLimit(2)
            .minimumScaleFactor(0.4)
            .multilineTextAlignment(.center)
            .foregroundColor(tile.isSolved ? .black : .primary)
            .padding(.horizontal, 4)
          Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        
        if isSelected {
          Image(systemName: "checkmark.circle.fill")
            .font(.caption)
            .foregroundColor(.blue)
            .padding(4)
        }
      }
      // Ensures the entire expanded rectangle registers tap gestures
      .contentShape(Rectangle())
    }
    .buttonStyle(.plain)
    // 🚀 Modifiers applied to the absolute outermost layer guarantee the shape stretches
    .frame(maxWidth: .infinity, maxHeight: .infinity)
    .background(
      tileShape
        .fill(tile.isSolved ? accentColor : Color.gray.opacity(0.2))
        .padding(.leading, mergesLeft ? -1.5 : 0)
        .padding(.trailing, mergesRight ? -1.5 : 0)
    )
    .overlay(
      tileShape
        .stroke(isSelected ? Color.blue : (tile.isSolved ? Color.clear : (endsWithParticle ? Color.orange.opacity(0.4) : Color.clear)), style: StrokeStyle(lineWidth: isSelected ? 3 : 1.5, dash: !isSelected && endsWithParticle ? [4, 2] : []))
        .padding(.leading, mergesLeft ? -1.5 : 0)
        .padding(.trailing, mergesRight ? -1.5 : 0)
    )
    .scaleEffect(tile.isSolved ? 1.02 : 1.0)
  }
  
  var body: some View {
    // 🚀 THE MAGIC: We only apply the aspect ratio locking in Portrait Mode!
    // In landscape, we return the button completely unconstrained.
    if useSquareAspectRatio {
      coreButton
        .aspectRatio(1.0, contentMode: .fit)
    } else {
      coreButton
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
