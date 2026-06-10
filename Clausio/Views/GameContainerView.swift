//
//  GameContainerView.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 10/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI

// MARK: - Game View Component
struct GameContainerView: View {
  @ObservedObject var vm: GameViewModel
  @Environment(\.verticalSizeClass) var verticalSizeClass
  
  var body: some View {
    Group {
      if verticalSizeClass == .compact {
        // MARK: - LANDSCAPE LAYOUT (Balanced Split Layout)
        HStack(spacing: 30) {
          boardGrid
            .frame(maxWidth: .infinity, maxHeight: .infinity)
          
          // Right Column: Content groups adjust to center automatically
          VStack(spacing: 20) {
            if vm.isLearnModeOn, vm.selectedIndex != nil {
              hudPanel
            }
            
            controlButtonsVertical
          }
          .frame(width: 110)
          .padding(.trailing, 10)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 15)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
      } else {
        // MARK: - PORTRAIT LAYOUT
        VStack(spacing: 20) {
          boardGrid
          hudPanel
          Spacer()
          controlButtonsHorizontal
        }
        .padding(.top, 10)
      }
    }
  }
  
  // MARK: - Extracted Component Subviews
  
  private var boardGrid: some View {
    VStack(spacing: vm.isAssistModeOn ? 2 : 10) {
      ForEach(0..<5, id: \.self) { row in
        HStack(spacing: vm.isAssistModeOn ? 2 : 8) {
          ForEach(0..<5, id: \.self) { col in
            let index = (row * 5) + col
            if index < vm.tiles.count {
              TileView(
                tile: vm.tiles[index],
                isSelected: vm.selectedIndex == index,
                accentColor: vm.colorForCategory(vm.tiles[index].categoryId),
                isAssistModeOn: vm.isAssistModeOn,
                mergesLeft: canMergeLeft(row: row, col: col),
                mergesRight: canMergeRight(row: row, col: col),
                action: {
                  withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                    vm.handleTap(at: index)
                  }
                }
              )
              .frame(maxWidth: .infinity, maxHeight: .infinity) // Fills allocated cell slots
            } else {
              Color.clear
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
          }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity) // 💡 FIXED: Dynamically stretches rows evenly
      }
    }
    .frame(maxWidth: .infinity, maxHeight: .infinity) // 💡 FIXED: Forces grid container to fill its split view boundary
    .padding(.horizontal, 4)
  }
  
  private var hudPanel: some View {
    Group {
      if vm.isLearnModeOn, let selected = vm.selectedIndex, selected < vm.tiles.count {
        VStack(alignment: .leading, spacing: 6) {
          VStack(alignment: .leading, spacing: 2) {
            Text("Furigana:")
              .font(.caption.bold())
              .foregroundColor(.secondary)
            Text(TileView.balancedJapaneseText(for: vm.tiles[selected].furigana, baseSize: 14, isSolved: vm.tiles[selected].isSolved))
          }
          VStack(alignment: .leading, spacing: 2) {
            Text("Meaning:")
              .font(.caption.bold())
              .foregroundColor(.secondary)
            Text(vm.tiles[selected].english)
              .font(.system(size: 13))
              .foregroundColor(.primary)
              .fixedSize(horizontal: false, vertical: true)
          }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 10).fill(Color.secondary.opacity(0.12)))
        .transition(.opacity.combined(with: .scale))
      }
      // 💡 FIXED: Removed the hardcoded fallback spacer that was un-centering the sidebar layout!
    }
  }
  
  private var controlButtonsHorizontal: some View {
    HStack(spacing: 40) {
      Button(action: { withAnimation(.easeInOut) { vm.shuffleIncorrectTiles() } }) {
        Image(systemName: "arrow.2.squarepath").font(.title)
      }
      Button(action: { withAnimation(.easeInOut) { vm.startNewGame() } }) {
        Image(systemName: "arrow.clockwise.circle.fill").font(.title).foregroundColor(.green)
      }
      Button(action: { withAnimation(.spring()) { vm.revealSolution() } }) {
        Image(systemName: "flag.fill").font(.title).foregroundColor(.blue)
      }
    }
    .padding(.bottom, 30)
  }
  
  private var controlButtonsVertical: some View {
    VStack(spacing: 28) {
      Button(action: { withAnimation(.easeInOut) { vm.shuffleIncorrectTiles() } }) {
        Image(systemName: "arrow.2.squarepath")
          .font(.title)
          .frame(width: 44, height: 44) // Clean, standardized target bounding box
      }
      Button(action: { withAnimation(.easeInOut) { vm.startNewGame() } }) {
        Image(systemName: "arrow.clockwise.circle.fill")
          .font(.title)
          .foregroundColor(.green)
          .frame(width: 44, height: 44)
      }
      Button(action: { withAnimation(.spring()) { vm.revealSolution() } }) {
        Image(systemName: "flag.fill")
          .font(.title)
          .foregroundColor(.blue)
          .frame(width: 44, height: 44)
      }
    }
    .frame(maxWidth: .infinity) // 💡 FIXED: Centers the vertical items inside the column block
  }
  
  private func canMergeLeft(row: Int, col: Int) -> Bool {
    let index = (row * 5) + col
    guard vm.isAssistModeOn, index < vm.tiles.count else { return false }
    let isCurrentCorrect = vm.tiles[index].correctIndex == index
    guard isCurrentCorrect && col > 0 else { return false }
    return vm.tiles[index - 1].correctIndex == index - 1
  }
  
  private func canMergeRight(row: Int, col: Int) -> Bool {
    let index = (row * 5) + col
    guard vm.isAssistModeOn, index < vm.tiles.count else { return false }
    let isCurrentCorrect = vm.tiles[index].correctIndex == index
    guard isCurrentCorrect && col < 4 else { return false }
    return vm.tiles[index + 1].correctIndex == index + 1
  }
}
