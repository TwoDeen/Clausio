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
  
  var body: some View {
    GeometryReader { geometry in
      // Dynamic cross-platform aspect verification
      let isWidescreen = geometry.size.width > geometry.size.height
      
      HStack(spacing: 0) {
        if isWidescreen {
          // MARK: - WIDESCREEN / MAC / LANDSCAPE LAYOUT
          HStack(spacing: 20) {
            boardGrid(useSquareLayout: false)
              .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            VStack(spacing: 16) {
              Spacer()
              if vm.isLearnModeOn, vm.selectedIndex != nil {
                hudPanel
              }
              controlButtonsVertical
              Spacer()
            }
            .frame(width: 120)
            .padding(.trailing, 10)
          }
          .padding(.horizontal, 20)
          .padding(.vertical, 15)
        } else {
          // MARK: - PORTRAIT LAYOUT
          VStack(spacing: 20) {
            boardGrid(useSquareLayout: true)
            hudPanel
            Spacer()
            controlButtonsHorizontal
          }
          .padding(.top, 10)
        }
      }
      .frame(width: geometry.size.width, height: geometry.size.height)
    }
  }
  
  // MARK: - Extracted Component Subviews
  
  @ViewBuilder
  private func boardGrid(useSquareLayout: Bool) -> some View {
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
                useSquareAspectRatio: useSquareLayout,
                action: {
                  withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                    vm.handleTap(at: index)
                  }
                }
              )
              .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
              // ✅ FIXED: Separated branches remove all inline 'nil' layout ambiguities
              if useSquareLayout {
                Color.clear
                  .aspectRatio(1.0, contentMode: .fit)
                  .frame(maxWidth: .infinity, maxHeight: .infinity)
              } else {
                Color.clear
                  .frame(maxWidth: .infinity, maxHeight: .infinity)
              }
            }
          }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
      }
    }
    .frame(maxWidth: .infinity, maxHeight: .infinity)
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
          .frame(width: 44, height: 44)
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
    .frame(maxWidth: .infinity)
  }
  
  // MARK: - Merge Detection Helpers
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
