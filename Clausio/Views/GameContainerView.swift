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
  
  // 🔊 Tracks which rows have already triggered auto-play, to avoid re-firing
  @State private var completedRows: Set<Int> = []
  
  // Snapshot used by onChange to detect solve-state transitions
  private var tilesSolvedState: [Bool] {
    vm.tiles.map(\.isSolved)
  }
  
  var body: some View {
    GeometryReader { geometry in
      let isWidescreen = geometry.size.width > geometry.size.height
      
      HStack(spacing: 0) {
        if isWidescreen {
          // MARK: - WIDESCREEN / LANDSCAPE LAYOUT
          HStack(spacing: 8) {
            
            boardGrid(useSquareLayout: false)
              .layoutPriority(1)
            
            // 🚀 PERFECTLY EVEN VERTICAL SPACING FLOW
            VStack(spacing: 0) {
              Spacer(minLength: 0)
              
              Group {
                // 1. Assist Mode Toggle
                modeIconToggle(icon: "puzzlepiece.extension.fill", isOn: $vm.isAssistModeOn)
                
                Spacer(minLength: 0)
                
                // 2. Learn Mode Toggle
                modeIconToggle(icon: "brain.head.profile", isOn: $vm.isLearnModeOn)
                
                Spacer(minLength: 0)
                
                // 3. Shuffle Button
                Button(action: { withAnimation(.easeInOut) { vm.shuffleIncorrectTiles() } }) {
                  Image(systemName: "shuffle")
                    .font(.title)
                    .frame(width: 44, height: 44)
                }
                
                Spacer(minLength: 0)
                
                // 4. New Game Button
                Button(action: { withAnimation(.easeInOut) { vm.startNewGame() } }) {
                  Image(systemName: "arrow.clockwise.circle.fill")
                    .font(.title)
                    .foregroundColor(.blue)
                    .frame(width: 44, height: 44)
                }
                
                Spacer(minLength: 0)
                
                // 5. Reveal Solution Button
                Button(action: { withAnimation(.spring()) { vm.revealSolution() } }) {
                  Image(systemName: "flag.fill")
                    .font(.title)
                    .foregroundColor(.blue)
                    .frame(width: 44, height: 44)
                }
              }
              
              Spacer(minLength: 0)
            }
            .frame(width: 56)
          }
          .padding(.horizontal, 8)
          .padding(.vertical, 10)
          
        } else {
          // MARK: - PORTRAIT LAYOUT
          VStack(spacing: 20) {
            
            boardGrid(useSquareLayout: true)
            
            modePillsBar
            
            Spacer()
            controlButtonsHorizontal
          }
          .padding(.top, 10)
        }
      }
      .frame(width: geometry.size.width, height: geometry.size.height)
    }
    .onChange(of: tilesSolvedState) { _ in
      detectNewlyCompletedRows()
    }
  }
  
  
  // MARK: - Board Grid Layout Builder
  @ViewBuilder
  private func boardGrid(useSquareLayout: Bool) -> some View {
    let hSpacing: CGFloat = vm.isAssistModeOn ? 2 : 8
    let vSpacing: CGFloat = vm.isAssistModeOn ? 2 : 10
    
    if useSquareLayout {
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
      GeometryReader { gridGeo in
        let availableWidth  = gridGeo.size.width
        let availableHeight = gridGeo.size.height
        let cellWidth  = max(0, (availableWidth  - (hSpacing * 4)) / 5)
        let cellHeight = max(0, (availableHeight - (vSpacing * 4)) / 5)
        
        VStack(spacing: vSpacing) {
          ForEach(0..<5, id: \.self) { row in
            HStack(spacing: hSpacing) {
              ForEach(0..<5, id: \.self) { col in
                let index = (row * 5) + col
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
        isAssistModeOn: vm.isLearnModeOn,
        mergesLeft: canMergeLeft(row: row, col: col),
        mergesRight: canMergeRight(row: row, col: col),
        useSquareAspectRatio: useSquareLayout,
        action: {
          withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
            vm.handleTap(at: index)
          }
        },
        onLongPress: {
          speakText(vm.tiles[index].text)
        }
      )
      .frame(maxWidth: .infinity, maxHeight: .infinity)
      .modifier(ShakeEffect(animatableData: (vm.selectedIndex == index && vm.errorMessage != nil) ? 1 : 0))
    } else {
      Color.clear
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
  }
  
  // MARK: - 🎛️ Mode Toggle Pills (Portrait — labeled, full-width pair)
  private var modePillsBar: some View {
    HStack(spacing: 10) {
      modePill(label: "Assist", icon: "puzzlepiece.extension.fill", isOn: $vm.isAssistModeOn)
      modePill(label: "Learn",  icon: "brain.head.profile",        isOn: $vm.isLearnModeOn)
    }
    .padding(.horizontal, 8)
  }
  
  private func modePill(label: String, icon: String, isOn: Binding<Bool>) -> some View {
    Button {
      withAnimation(.spring(response: 0.3, dampingFraction: 0.65)) {
        isOn.wrappedValue.toggle()
      }
    } label: {
      HStack(spacing: 5) {
        Image(systemName: icon).font(.caption.bold())
        Text(label).font(.caption.bold())
      }
      .padding(.horizontal, 12)
      .padding(.vertical, 7)
      .frame(maxWidth: .infinity)
      .background(
        Capsule().fill(isOn.wrappedValue ? Color.accentColor.opacity(0.12) : Color.secondary.opacity(0.1))
      )
      .overlay(
        Capsule().strokeBorder(isOn.wrappedValue ? Color.accentColor.opacity(0.5) : Color.clear, lineWidth: 1)
      )
      .foregroundColor(isOn.wrappedValue ? .accentColor : .secondary)
    }
    .buttonStyle(.plain)
  }
  
  // MARK: - 🎛️ Mode Toggle Icons (Landscape Configuration Tool)
  private func modeIconToggle(icon: String, isOn: Binding<Bool>) -> some View {
    Button {
      withAnimation(.spring(response: 0.3, dampingFraction: 0.65)) {
        isOn.wrappedValue.toggle()
      }
    } label: {
      Image(systemName: icon)
        .font(.body)
        .frame(width: 36, height: 36)
        .background(
          Circle().fill(isOn.wrappedValue ? Color.accentColor.opacity(0.12) : Color.secondary.opacity(0.1))
        )
        .overlay(
          Circle().strokeBorder(isOn.wrappedValue ? Color.accentColor.opacity(0.5) : Color.clear, lineWidth: 1)
        )
        .foregroundColor(isOn.wrappedValue ? .accentColor : .secondary)
    }
    .buttonStyle(.plain)
  }
  
  // MARK: - 🔊 Row Completion Auto-Play
  private func detectNewlyCompletedRows() {
    guard vm.tiles.count == 25 else { return }
    
    // Game was reset — clear the completed-row registry
    if vm.tiles.allSatisfy({ !$0.isSolved }) {
      completedRows = []
      return
    }
    
    for row in 0..<5 {
      guard !completedRows.contains(row) else { continue }
      let rowComplete = (0..<5).allSatisfy { col in
        vm.tiles[(row * 5) + col].isSolved
      }
      guard rowComplete else { continue }
      
      completedRows.insert(row)
    }
  }
  
  // MARK: - Interface Control Layout Blocks (Portrait Layout Tool)
  private var controlButtonsHorizontal: some View {
    HStack(spacing: 40) {
      Button(action: { withAnimation(.easeInOut) { vm.shuffleIncorrectTiles() } }) {
        Image(systemName: "shuffle").font(.title)
      }
      Button(action: { withAnimation(.easeInOut) { vm.startNewGame() } }) {
        Image(systemName: "arrow.clockwise.circle.fill").font(.title).foregroundColor(.blue)
      }
      Button(action: { withAnimation(.spring()) { vm.revealSolution() } }) {
        Image(systemName: "flag.fill").font(.title).foregroundColor(.blue)
      }
    }
    .padding(.bottom, 30)
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
