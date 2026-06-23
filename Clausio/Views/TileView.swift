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
  // MARK: - Properties
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
  
  // MARK: - Styling Helpers
  private var currentBackgroundColor: Color {
    tile.isSolved ? accentColor : Color.gray.opacity(0.2)
  }
  
  private var currentBorderColor: Color {
    if isSelected {
      return .blue
    } else if tile.isSolved {
      return .clear
    } else if endsWithParticle {
      return .orange.opacity(0.4)
    } else {
      return .clear
    }
  }
  
  private var currentStrokeStyle: StrokeStyle {
    let lineWidth: CGFloat = isSelected ? 3 : 1.5
    let dashes: [CGFloat] = (!isSelected && endsWithParticle) ? [4, 2] : []
    return StrokeStyle(lineWidth: lineWidth, dash: dashes)
  }
  
  // MARK: - Core Content Presentation Layer
  private var coreButton: some View {
    ZStack(alignment: .topTrailing) {
      
      // Removed the grammar tag from inside the ZStack to prevent layout collapsing
      
      // Main Text Wrapper
      VStack(spacing: 0) {
        Spacer(minLength: 0)
        
        if isAssistModeOn && !tile.furigana.isEmpty {
          RubyTextView(kanji: tile.text, furigana: tile.furigana)
            .multilineTextAlignment(.center)
            .padding(.horizontal, 4)
            .minimumScaleFactor(0.35)
        } else {
          Text(Self.balancedJapaneseText(for: tile.text, baseSize: 15, isSolved: tile.isSolved))
            .lineLimit(3)
            .minimumScaleFactor(0.3)
            .multilineTextAlignment(.center)
            .foregroundColor(tile.isSolved ? .black : .primary)
            .padding(.horizontal, 4)
        }
        
        Spacer(minLength: 0)
      }
      .frame(maxWidth: .infinity, maxHeight: .infinity)
      
      // Selection Checkmark
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
        .fill(currentBackgroundColor)
        .padding(.leading, mergesLeft ? -1.5 : 0)
        .padding(.trailing, mergesRight ? -1.5 : 0)
    )
    .overlay(
      tileShape
        .stroke(currentBorderColor, style: currentStrokeStyle)
        .padding(.leading, mergesLeft ? -1.5 : 0)
        .padding(.trailing, mergesRight ? -1.5 : 0)
    )
    // 🚀 THE FIX: Explicit Top-Leading Overlay ensures it never gets pushed out of bounds
    .overlay(alignment: .topLeading) {
      if tile.isSolved {
        if tile.originalColumnId == 1 || tile.originalColumnId == 0 {
          // 🚀 Pointing to the newly renamed camelCase property
          Text(tile.sentenceIndividualGrammarLevel ?? "N/A")
            .font(.system(size: 11, weight: .black, design: .rounded))
            .foregroundColor(.black)
            .padding(.top, 4)
            .padding(.leading, 6)
        }
      }
    }
    .scaleEffect(tile.isSolved ? 1.02 : 1.0)
    .onTapGesture {
      action()
    }
  }
  
  // MARK: - Body
  var body: some View {
    if useSquareAspectRatio {
      coreButton
        .aspectRatio(1.0, contentMode: .fit)
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
        singleCharString.font = .system(size: baseSize)
      }
      combinedString.append(singleCharString)
    }
    return combinedString
  }
}

// MARK: - Extensions
extension TileView {
  struct RubyTextView: View {
    let kanji: String
    let furigana: String
    
    var body: some View {
      VStack(alignment: .center, spacing: 1) {
        Text(furigana)
          .font(.system(size: 10, weight: .medium))
          .foregroundColor(.blue)
          .minimumScaleFactor(0.5)
          .lineLimit(1)
        
        Text(kanji)
          .font(.system(size: 16, weight: .regular))
          .foregroundColor(.primary)
      }
    }
  }
}
