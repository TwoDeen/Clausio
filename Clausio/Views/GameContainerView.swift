//
//  GameContainerView.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 12/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI
import AVFoundation

// MARK: - Functional Error Shake Animation
struct ShakeEffect: GeometryEffect {
  var amount: CGFloat = 10
  var shakesPerUnit = 3
  var animatableData: CGFloat
  
  func effectValue(size: CGSize) -> ProjectionTransform {
    ProjectionTransform(CGAffineTransform(translationX:
                                            amount * sin(animatableData * .pi * CGFloat(shakesPerUnit)), y: 0))
  }
}

// MARK: - Main Game Container View
struct GameContainerView: View {
  @ObservedObject var vm: GameViewModel
  @State private var speechSynthesizer = AVSpeechSynthesizer()
  
  var body: some View {
    GeometryReader { geometry in
      let isWidescreen = geometry.size.width > geometry.size.height
      
      HStack(spacing: 0) {
        if isWidescreen {
          // MARK: - WIDESCREEN / LANDSCAPE LAYOUT
          HStack(spacing: 24) {
            
            // Layout is purely driven by raw math and explicit Geometry pixel bounds.
            boardGrid(useSquareLayout: false)
              .layoutPriority(1)
            
            VStack(spacing: 16) {
              Spacer()
              if vm.isLearnModeOn, vm.selectedIndex != nil {
                hudPanel
              }
              controlButtonsVertical
              Spacer()
            }
            .frame(width: 140)
            .padding(.trailing, 10)
          }
          .padding(.horizontal, 20)
          .padding(.vertical, 15)
          
        } else {
          // MARK: - PORTRAIT LAYOUT
          VStack(spacing: 20) {
            
            boardGrid(useSquareLayout: true)
            
            if vm.isLearnModeOn, vm.selectedIndex != nil {
              hudPanel
            }
            
            Spacer()
            controlButtonsHorizontal
          }
          .padding(.top, 10)
        }
      }
      .frame(width: geometry.size.width, height: geometry.size.height)
    }
  }
  
  // MARK: - Board Grid Layout Builder
  @ViewBuilder
  private func boardGrid(useSquareLayout: Bool) -> some View {
    let hSpacing: CGFloat = vm.isAssistModeOn ? 2 : 8
    let vSpacing: CGFloat = vm.isAssistModeOn ? 2 : 10
    
    if useSquareLayout {
      // 📱 PORTRAIT: Standard layout safely maintains square aspect ratios based on screen width
      VStack(spacing: vSpacing) {
        ForEach(0..<5, id: \.self) { row in
          HStack(spacing: hSpacing) {
            ForEach(0..<5, id: \.self) { col in
              let index = (row * 5) + col
              tileCell(at: index, useSquareLayout: true)
            }
          }
        }
      }
    } else {
      // 🚀 LANDSCAPE: Explicit Geometry Math Override
      GeometryReader { gridGeo in
        let availableWidth = gridGeo.size.width
        let availableHeight = gridGeo.size.height
        
        let cellWidth = max(0, (availableWidth - (hSpacing * 4)) / 5)
        let cellHeight = max(0, (availableHeight - (vSpacing * 4)) / 5)
        
        VStack(spacing: vSpacing) {
          ForEach(0..<5, id: \.self) { row in
            HStack(spacing: hSpacing) {
              ForEach(0..<5, id: \.self) { col in
                let index = (row * 5) + col
                
                // Explicit framing overrides all native intrinsic squishing
                tileCell(at: index, useSquareLayout: false)
                  .frame(width: cellWidth, height: cellHeight)
              }
            }
          }
        }
        .frame(width: availableWidth, height: availableHeight, alignment: .center)
      }
    }
  }
  
  // MARK: - Unified Tile Cell Rendering Framework
  @ViewBuilder
  private func tileCell(at index: Int, useSquareLayout: Bool) -> some View {
    if index < vm.tiles.count {
      let row = index / 5
      let col = index % 5
      
      TileView(
        tile: vm.tiles[index],
        isSelected: vm.selectedIndex == index,
        accentColor: vm.colorForCategory(vm.tiles[index].originalRowId),
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
      .modifier(ShakeEffect(animatableData: (vm.selectedIndex == index && vm.errorMessage != nil) ? 1 : 0))
    } else {
      Color.clear
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
  }
  
  // MARK: - Contextual Learning Assistant Panel (HUD)
  private var hudPanel: some View {
    Group {
      if let selected = vm.selectedIndex, selected < vm.tiles.count {
        VStack(alignment: .leading, spacing: 6) {
          HStack {
            VStack(alignment: .leading, spacing: 2) {
              Text("Furigana Reading:")
                .font(.caption.bold())
                .foregroundColor(.secondary)
                .fixedSize(horizontal: true, vertical: false)
              
              Text(TileView.balancedJapaneseText(for: vm.tiles[selected].furigana, baseSize: 14, isSolved: vm.tiles[selected].isSolved))
            }
            Spacer()
            
            Button(action: { speakText(vm.tiles[selected].text) }) {
              Image(systemName: "speaker.wave.2.bubble.left.fill")
                .font(.body)
                .foregroundColor(.accentColor)
                .padding(6)
                .background(Color.accentColor.opacity(0.1))
                .clipShape(Circle())
            }
            .buttonStyle(.plain)
          }
          
          VStack(alignment: .leading, spacing: 2) {
            Text("Clause Context:")
              .font(.caption.bold())
              .foregroundColor(.secondary)
              .fixedSize(horizontal: true, vertical: false)
            
            Text(vm.tiles[selected].text)
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
  
  // MARK: - Interface Control Layout Blocks
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
  
  // MARK: - Native AVSpeech Engine Orchestration
  private func speakText(_ text: String) {
    if speechSynthesizer.isSpeaking {
      speechSynthesizer.stopSpeaking(at: .immediate)
    }
    let utterance = AVSpeechUtterance(string: text)
    utterance.voice = AVSpeechSynthesisVoice(language: "ja-JP")
    utterance.rate = 0.42
    speechSynthesizer.speak(utterance)
  }
  
  // MARK: - Grammar Chunk Merging Calculations
  private func canMergeLeft(row: Int, col: Int) -> Bool {
    let currentIndex = (row * 5) + col
    guard vm.isAssistModeOn, currentIndex < vm.tiles.count else { return false }
    
    let currentTile = vm.tiles[currentIndex]
    let isCurrentCorrect = currentTile.originalRowId == (row + 1) && currentTile.originalColumnId == (col + 1)
    
    guard isCurrentCorrect && col > 0 else { return false }
    
    let leftTile = vm.tiles[currentIndex - 1]
    return leftTile.originalRowId == (row + 1) && leftTile.originalColumnId == col
  }
  
  private func canMergeRight(row: Int, col: Int) -> Bool {
    let currentIndex = (row * 5) + col
    guard vm.isAssistModeOn, currentIndex < vm.tiles.count else { return false }
    
    let currentTile = vm.tiles[currentIndex]
    let isCurrentCorrect = currentTile.originalRowId == (row + 1) && currentTile.originalColumnId == (col + 1)
    
    guard isCurrentCorrect && col < 4 else { return false }
    
    let rightTile = vm.tiles[currentIndex + 1]
    return rightTile.originalRowId == (row + 1) && rightTile.originalColumnId == (col + 2)
  }
}
