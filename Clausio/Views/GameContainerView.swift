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
    VStack(spacing: 20) {
      Text("Japanese Connections")
        .font(.title2.bold())
        .padding(.top)
      
      // 5x5 Puzzle Board
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
              } else {
                Color.clear
                  .aspectRatio(1.0, contentMode: .fit)
              }
            }
          }
        }
      }
      .padding(.horizontal, 4)
      
      // HUD Info Panel for Learn Mode
      if vm.isLearnModeOn, let selected = vm.selectedIndex, selected < vm.tiles.count {
        VStack(spacing: 6) {
          // Furigana Layout Row using the shared typography engine
          HStack(spacing: 4) {
            Text("Furigana: ")
              .font(.system(size: 14, weight: .bold))
              .foregroundColor(.secondary)
            
            Text(TileView.balancedJapaneseText(for: vm.tiles[selected].furigana, baseSize: 16, isSolved: vm.tiles[selected].isSolved))
          }
          
          // Meaning Layout Row
          HStack(spacing: 4) {
            Text("Meaning: ")
              .font(.system(size: 14, weight: .bold))
              .foregroundColor(.secondary)
            Text(vm.tiles[selected].english)
              .font(.system(size: 14))
              .foregroundColor(.primary)
          }
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(RoundedRectangle(cornerRadius: 12).fill(Color.secondary.opacity(0.15)))
        .transition(.opacity.combined(with: .scale))
      } else {
        // Uniform layout constraint fallback to block screen jittering
        Spacer().frame(height: 74)
      }
      
      Spacer()
      
      // Control Buttons
      HStack(spacing: 40) {
        // Shuffle Button
        Button(action: {
          withAnimation(.easeInOut) { vm.shuffleIncorrectTiles() }
        }) {
          Image(systemName: "arrow.2.squarepath")
            .font(.title)
        }
        
        // New Game Button
        Button(action: {
          withAnimation(.easeInOut) { vm.startNewGame() }
        }) {
          Image(systemName: "arrow.clockwise.circle.fill")
            .font(.title)
            .foregroundColor(.green)
        }
        
        // Reveal Solution (Give Up) Button
        Button(action: {
          withAnimation(.spring()) { vm.revealSolution() }
        }) {
          Image(systemName: "flag.fill")
            .font(.title)
            .foregroundColor(.blue)
        }
      }
      .padding(.bottom, 30)
    }
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
