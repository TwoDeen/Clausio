//
//  TileView.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 10/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI
import CoreText


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
  let onLongPress: () -> Void
  
  private var endsWithParticle: Bool {
    let particles = ["を", "に", "が", "は", "と", "で", "へ", "の", "も", "か", "ね", "よ"]
    return particles.contains { tile.text.hasSuffix($0) }
  }
  
  // MARK: - Core Content Presentation Layer (Fixed Gesture Layer)
  private var coreButton: some View {
    // 🚀 CHANGED: Swapped Button for a content wrapper to handle combined gestures cleanly
    ZStack(alignment: .topTrailing) {
      
      // Forces the label to push out to the exact edges of the cell frame
      VStack(spacing: 0) {
        Spacer(minLength: 0)
        
        // Check if Learn Mode is on AND Furigana is available
        if isAssistModeOn && !tile.furigana.isEmpty {
          RubyTextView(kanji: tile.text, furigana: tile.furigana)
            .multilineTextAlignment(.center)
            .padding(.horizontal, 4)
            .minimumScaleFactor(0.35)
        } else {
          // Standard fallback using your core balanced Japanese stroke font system
          Text(Self.balancedJapaneseText(for: tile.text, baseSize: 15, isSolved: tile.isSolved))
            .lineLimit(3)
            .minimumScaleFactor(0.2)
            .multilineTextAlignment(.center)
            .foregroundColor(tile.isSolved ? .black : .primary)
            .padding(.horizontal, 4)
        }
        
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
    .contentShape(Rectangle())
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
    // 🚀 THE FIX: Handles the selection tap action directly without a standard Button container
    .onTapGesture {
      action()
    }
  }
  
  
  var body: some View {
    if useSquareAspectRatio {
      coreButton
        .aspectRatio(1.0, contentMode: .fit)
      // 🚀 Trigger speech sequence callback smoothly on long-press
        .onLongPressGesture(minimumDuration: 0.4) {
          onLongPress()
        }
    } else {
      coreButton
        .onLongPressGesture(minimumDuration: 0.4) {
          onLongPress()
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
        // Fall back to the system font so Hiragana/Katakana render properly
        singleCharString.font = .system(size: baseSize)
      }
      combinedString.append(singleCharString)
    }
    return combinedString
  }
}



extension TileView {
  // Add this helper struct at the bottom of TileView.swift
  struct RubyTextView: View {
    let kanji: String
    let furigana: String
    
    var body: some View {
      VStack(alignment: .center, spacing: 1) {
        // Small Furigana floating on top
        Text(furigana)
          .font(.system(size: 10, weight: .medium))
          .foregroundColor(.blue)
          .minimumScaleFactor(0.5)
          .lineLimit(1)
        
        // Main Kanji text below
        Text(kanji)
          .font(.system(size: 16, weight: .regular))
          .foregroundColor(.primary)
      }
    }
  }
}

