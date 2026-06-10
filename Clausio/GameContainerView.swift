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
              TileView(
                tile: vm.tiles[index],
                isSelected: vm.selectedIndex == index,
                accentColor: vm.colorForCategory(vm.tiles[index].categoryId),
                isAssistModeOn: vm.isAssistModeOn,
                action: { vm.handleTap(at: index) }
              )
            }
          }
        }
      }
      .padding(.horizontal, 4)
      
      // HUD Info Panel for Learn Mode
      if vm.isLearnModeOn, let selected = vm.selectedIndex {
        
        
        VStack(spacing: 4) {
          Text("Furigana: \(vm.tiles[selected].furigana)")
            .font(.notoCcSans(.bold, size: 16)) // Uses your custom font
          Text("Meaning: \(vm.tiles[selected].english)")
            .font(.system(size: 14)) // Kept system style for clean English contrast
            .foregroundColor(.secondary)
        }
        .padding()
        .background(RoundedRectangle(cornerRadius: 12).fill(Color.secondary.opacity(0.15)))
        .transition(.opacity.combined(with: .scale))
      } else {
        Spacer().frame(height: 70)
      }
      
      Spacer()
      
      // MARK: - Game View Component (Inside struct GameContainerView)
      
      // Control Buttons
      HStack(spacing: 40) {
        // Shuffle Button
        Button(action: vm.shuffleIncorrectTiles) {
          Image(systemName: "arrow.2.squarepath")
            .font(.title)
        }
        
        // New Game Button
        Button(action: vm.startNewGame) {
          Image(systemName: "arrow.clockwise.circle.fill") // Fresh restart icon
            .font(.title)
            .foregroundColor(.green)
        }
        
        // Reveal Solution (Give Up) Button
        Button(action: vm.revealSolution) {
          Image(systemName: "flag.fill") // Swapped xmark for flag
            .font(.title)
            .foregroundColor(.blue)
        }
      }
      .padding(.bottom, 30)
    }
  }
}
