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
              
              // Safe check bounds to prevent runtime array indexing crashes
              if index < vm.tiles.count {
                TileView(
                  tile: vm.tiles[index],
                  isSelected: vm.selectedIndex == index,
                  accentColor: vm.colorForCategory(vm.tiles[index].categoryId),
                  isAssistModeOn: vm.isAssistModeOn,
                  action: {
                    // Animate selection to enable smooth HUD appearance transitions
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
        VStack(spacing: 4) {
          Text("Furigana: \(vm.tiles[selected].furigana)")
            .font(.notoCcSans(.bold, size: 16))
          Text("Meaning: \(vm.tiles[selected].english)")
            .font(.system(size: 14))
            .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(RoundedRectangle(cornerRadius: 12).fill(Color.secondary.opacity(0.15)))
        .transition(.opacity.combined(with: .scale))
      } else {
        // Keeps frame heights uniform to prevent layout shifts when selections toggle
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
}
