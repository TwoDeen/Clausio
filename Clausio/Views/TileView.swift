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
        VStack {
          Spacer()
          Text(tile.text)
            .font(.custom(isBold ? "japaneseSVGFont-Bold" : "japaneseSVGFont", size: 28))
            .minimumScaleFactor(0.5)
            .multilineTextAlignment(.center)
            .foregroundColor(tile.isSolved ? .black : .primary)
          Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
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
    .disabled(tile.isSolved)
  }
}

extension Font {
  static func notoCcSans(_ style: NotoStyle, size: CGFloat) -> Font {
    return .custom(style.rawValue, size: size)
  }
  
  enum NotoStyle: String {
    case regular = "japaneseSVGFont" // Match your PostScript name exactly
    case bold = "japaneseSVGFont-Bold"
  }
}
