//
//  GameContainerView.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 12/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI
import AVFoundation
#if os(iOS)
import UIKit
#elseif os(macOS)
import AppKit
#endif

// MARK: - Functional Error Shake Animation
struct ShakeEffect: GeometryEffect {
  var amount: CGFloat = 10
  var shakesPerUnit = 3
  var animatableData: CGFloat
  
  func effectValue(size: CGSize) -> ProjectionTransform {
    ProjectionTransform(
      CGAffineTransform(
        translationX: amount * sin(animatableData * .pi * CGFloat(shakesPerUnit)),
        y: 0
      )
    )
  }
}

// MARK: - Main Game Container View
struct GameContainerView: View {
  @ObservedObject var vm: GameViewModel
  @State private var speechSynthesizer = AVSpeechSynthesizer()
  
  @State private var completedRows: Set<Int> = []
  @State private var copiedRowIndex: Int? = nil
  @State private var showingPassageSheet = false
  
  private var tilesSolvedState: [Bool] {
    vm.tiles.map(\.isSolved)
  }
  
  var body: some View {
    GeometryReader { geometry in
      let isWidescreen = geometry.size.width > geometry.size.height
      
      HStack(spacing: 0) {
        if isWidescreen {
          HStack(spacing: 8) {
            boardGrid(useSquareLayout: false)
              .layoutPriority(1)
            
            VStack(spacing: 0) {
              Spacer(minLength: 0)
              
              Group {
                modeIconToggle(icon: "puzzlepiece.extension.fill", isOn: $vm.isAssistModeOn)
                
                Spacer(minLength: 0)
                
                modeIconToggle(icon: "brain.head.profile", isOn: $vm.isLearnModeOn)
                
                Spacer(minLength: 0)
                
                Button(action: {
                  withAnimation(.easeInOut) {
                    vm.shuffleIncorrectTiles()
                  }
                }) {
                  Image(systemName: "shuffle")
                    .font(.title)
                    .frame(width: 44, height: 44)
                }
                
                Spacer(minLength: 0)
                
                Button(action: {
                  withAnimation(.easeInOut) {
                    vm.startNewGame()
                  }
                }) {
                  Image(systemName: "arrow.clockwise.circle.fill")
                    .font(.title)
                    .foregroundColor(.blue)
                    .frame(width: 44, height: 44)
                }
                
                Spacer(minLength: 0)
                
                Button(action: {
                  withAnimation(.spring()) {
                    vm.revealSolution()
                  }
                }) {
                  Image(systemName: "flag.fill")
                    .font(.title)
                    .foregroundColor(.blue)
                    .frame(width: 44, height: 44)
                }
                
                Spacer(minLength: 0)
                
                Button(action: {
                  showingPassageSheet = true
                }) {
                  Image(systemName: "doc.text.magnifyingglass")
                    .font(.title)
                    .foregroundColor(.blue)
                    .frame(width: 44, height: 44)
                }
                .accessibilityLabel("View entire passage")
                .help("View entire passage")
                
                Spacer(minLength: 0)
              }
              .frame(width: 56)
              .padding(.horizontal, 8)
              .padding(.vertical, 10)
            }
          }
          .frame(width: geometry.size.width, height: geometry.size.height)
        } else {
          VStack(spacing: 20) {
            boardGrid(useSquareLayout: true)
            modePillsBar
            Spacer()
            controlButtonsHorizontal
          }
          .padding(.top, 10)
          .frame(width: geometry.size.width, height: geometry.size.height)
        }
      }
      .onChange(of: tilesSolvedState) { _ in
        detectNewlyCompletedRows()
      }
    }
    .sheet(isPresented: $showingPassageSheet) {
      PassageSheetView(
        rows: vm.passageRows,
        plainPassageText: vm.fullPassageText,
        hasFurigana: vm.hasFuriganaPassage
      )
    }
  }
  
  @ViewBuilder
  private func boardGrid(useSquareLayout: Bool) -> some View {
    let hSpacing: CGFloat = vm.isAssistModeOn ? 2 : 8
    let vSpacing: CGFloat = vm.isAssistModeOn ? 2 : 10
    let rowActionSpacing: CGFloat = 6
    
    if useSquareLayout {
      VStack(spacing: vSpacing) {
        ForEach(0..<5, id: \.self) { row in
          HStack(spacing: rowActionSpacing) {
            HStack(spacing: hSpacing) {
              ForEach(0..<5, id: \.self) { col in
                let index = (row * 5) + col
                tileCell(at: index, useSquareLayout: true)
              }
            }
            
            rowCopyButton(for: row)
          }
        }
      }
      .padding(.horizontal, 8)
    } else {
      GeometryReader { gridGeo in
        let availableWidth = gridGeo.size.width
        let availableHeight = gridGeo.size.height
        
        let copyButtonWidth: CGFloat = 30
        let tileRegionWidth = max(0, availableWidth - copyButtonWidth - rowActionSpacing)
        let cellWidth = max(0, (tileRegionWidth - (hSpacing * 4)) / 5)
        let cellHeight = max(0, (availableHeight - (vSpacing * 4)) / 5)
        
        VStack(spacing: vSpacing) {
          ForEach(0..<5, id: \.self) { row in
            HStack(spacing: rowActionSpacing) {
              HStack(spacing: hSpacing) {
                ForEach(0..<5, id: \.self) { col in
                  let index = (row * 5) + col
                  tileCell(at: index, useSquareLayout: false)
                    .frame(width: cellWidth, height: cellHeight)
                }
              }
              
              rowCopyButton(for: row)
                .frame(width: copyButtonWidth, height: cellHeight)
            }
          }
        }
        .frame(width: availableWidth, height: availableHeight, alignment: .center)
      }
    }
  }
  
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
      .modifier(
        ShakeEffect(
          animatableData: (vm.selectedIndex == index && vm.errorMessage != nil) ? 1 : 0
        )
      )
    } else {
      Color.clear
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
  }
  
  @ViewBuilder
  private func rowCopyButton(for row: Int) -> some View {
    Button(action: {
      copySentenceForRow(row)
    }) {
      Image(systemName: copiedRowIndex == row ? "checkmark.circle.fill" : "doc.on.doc")
        .font(.caption.bold())
        .foregroundColor(copiedRowIndex == row ? .green : .secondary)
        .frame(width: 28, height: 28)
        .background(
          Circle().fill(Color.secondary.opacity(0.10))
        )
    }
    .buttonStyle(.plain)
    .accessibilityLabel("Copy full sentence for row \(row + 1)")
    .help("Copy full sentence for row \(row + 1)")
  }
  
  private func copySentenceForRow(_ row: Int) {
    let sentence = vm.fullSentenceForRow(row)
    guard !sentence.isEmpty else { return }
    
#if os(iOS)
    UIPasteboard.general.string = sentence
#elseif os(macOS)
    NSPasteboard.general.clearContents()
    NSPasteboard.general.setString(sentence, forType: .string)
#endif
    
    copiedRowIndex = row
    
    DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
      if copiedRowIndex == row {
        copiedRowIndex = nil
      }
    }
  }
  
  private var modePillsBar: some View {
    HStack(spacing: 10) {
      modePill(label: "Assist", icon: "puzzlepiece.extension.fill", isOn: $vm.isAssistModeOn)
      modePill(label: "Learn", icon: "brain.head.profile", isOn: $vm.isLearnModeOn)
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
        Image(systemName: icon)
          .font(.caption.bold())
        Text(label)
          .font(.caption.bold())
      }
      .padding(.horizontal, 12)
      .padding(.vertical, 7)
      .frame(maxWidth: .infinity)
      .background(
        Capsule().fill(
          isOn.wrappedValue
          ? Color.accentColor.opacity(0.12)
          : Color.secondary.opacity(0.1)
        )
      )
      .overlay(
        Capsule().strokeBorder(
          isOn.wrappedValue
          ? Color.accentColor.opacity(0.5)
          : Color.clear,
          lineWidth: 1
        )
      )
      .foregroundColor(isOn.wrappedValue ? .accentColor : .secondary)
    }
    .buttonStyle(.plain)
  }
  
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
          Circle().fill(
            isOn.wrappedValue
            ? Color.accentColor.opacity(0.12)
            : Color.secondary.opacity(0.1)
          )
        )
        .overlay(
          Circle().strokeBorder(
            isOn.wrappedValue
            ? Color.accentColor.opacity(0.5)
            : Color.clear,
            lineWidth: 1
          )
        )
        .foregroundColor(isOn.wrappedValue ? .accentColor : .secondary)
    }
    .buttonStyle(.plain)
  }
  
  private func detectNewlyCompletedRows() {
    guard vm.tiles.count == 25 else { return }
    
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
      speakText(vm.fullSentenceForRow(row))
    }
  }
  
  private var controlButtonsHorizontal: some View {
    HStack(spacing: 40) {
      Button(action: {
        withAnimation(.easeInOut) {
          vm.shuffleIncorrectTiles()
        }
      }) {
        Image(systemName: "shuffle")
          .font(.title)
      }
      
      Button(action: {
        withAnimation(.easeInOut) {
          vm.startNewGame()
        }
      }) {
        Image(systemName: "arrow.clockwise.circle.fill")
          .font(.title)
          .foregroundColor(.blue)
      }
      
      Button(action: {
        withAnimation(.spring()) {
          vm.revealSolution()
        }
      }) {
        Image(systemName: "flag.fill")
          .font(.title)
          .foregroundColor(.blue)
      }
      
      Button(action: {
        showingPassageSheet = true
      }) {
        Image(systemName: "doc.text.magnifyingglass")
          .font(.title)
          .foregroundColor(.blue)
      }
      .accessibilityLabel("View entire passage")
      .help("View entire passage")
    }
    .padding(.bottom, 30)
  }
  
  private func speakText(_ text: String) {
    if speechSynthesizer.isSpeaking {
      speechSynthesizer.stopSpeaking(at: .immediate)
    }
    
    let utterance = AVSpeechUtterance(string: text)
    utterance.voice = AVSpeechSynthesisVoice(language: "ja-JP")
    utterance.rate = 0.42
    speechSynthesizer.speak(utterance)
  }
  
  private func canMergeLeft(row: Int, col: Int) -> Bool {
    let currentIndex = (row * 5) + col
    guard vm.isAssistModeOn, currentIndex < vm.tiles.count else { return false }
    
    let currentTile = vm.tiles[currentIndex]
    let isCurrentCorrect =
    currentTile.originalRowId == (row + 1) &&
    currentTile.originalColumnId == (col + 1)
    
    guard isCurrentCorrect && col > 0 else { return false }
    
    let leftTile = vm.tiles[currentIndex - 1]
    return leftTile.originalRowId == (row + 1) && leftTile.originalColumnId == col
  }
  
  private func canMergeRight(row: Int, col: Int) -> Bool {
    let currentIndex = (row * 5) + col
    guard vm.isAssistModeOn, currentIndex < vm.tiles.count else { return false }
    
    let currentTile = vm.tiles[currentIndex]
    let isCurrentCorrect =
    currentTile.originalRowId == (row + 1) &&
    currentTile.originalColumnId == (col + 1)
    
    guard isCurrentCorrect && col < 4 else { return false }
    
    let rightTile = vm.tiles[currentIndex + 1]
    return rightTile.originalRowId == (row + 1) && rightTile.originalColumnId == (col + 2)
  }
}

// MARK: - Passage Sheet
struct PassageSheetView: View {
  let rows: [[Tile]]
  let plainPassageText: String
  let hasFurigana: Bool
  
  @State private var showFurigana = false
  @Environment(\.dismiss) private var dismiss
  
  var body: some View {
    NavigationView {
      ScrollView {
        VStack(alignment: .leading, spacing: 16) {
          if hasFurigana {
            Toggle("Show Furigana", isOn: $showFurigana)
          }
          
          if rows.isEmpty {
            Text("Passage unavailable.")
              .foregroundColor(.secondary)
          } else if showFurigana && hasFurigana {
            RubyPassageView(rows: rows)
          } else {
            Text(plainPassageText)
              .font(.body)
              .frame(maxWidth: .infinity, alignment: .leading)
              .textSelection(.enabled)
          }
        }
        .padding()
      }
      .navigationTitle("Passage")
      .navigationBarTitleDisplayMode(.inline)
      .toolbar {
        ToolbarItem(placement: .navigationBarTrailing) {
          Button("Done") {
            dismiss()
          }
        }
      }
    }
  }
}

// MARK: - Ruby Passage Renderer
struct RubyPassageView: View {
  let rows: [[Tile]]
  
  var body: some View {
    VStack(alignment: .leading, spacing: 18) {
      ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
        RubyRowView(tokens: row)
      }
    }
    .frame(maxWidth: .infinity, alignment: .leading)
  }
}

struct RubyRowView: View {
  let tokens: [Tile]
  
  var body: some View {
    ScrollView(.horizontal, showsIndicators: false) {
      HStack(alignment: .bottom, spacing: 2) {
        ForEach(Array(tokens.enumerated()), id: \.offset) { _, tile in
          RubyTokenView(surface: tile.text, reading: normalizedReading(for: tile))
        }
      }
      .frame(maxWidth: .infinity, alignment: .leading)
    }
  }
  
  private func normalizedReading(for tile: Tile) -> String? {
    let trimmed = tile.furigana.trimmingCharacters(in: .whitespacesAndNewlines)
    if trimmed.isEmpty || trimmed == tile.text {
      return nil
    }
    return trimmed
  }
}

struct RubyTokenView: View {
  let surface: String
  let reading: String?
  
  var body: some View {
    VStack(spacing: 0) {
      if let reading {
        Text(reading)
          .font(.caption2)
          .foregroundColor(.blue)
          .lineLimit(1)
          .fixedSize()
      } else {
        Text(" ")
          .font(.caption2)
          .hidden()
      }
      
      Text(surface)
        .font(.body)
        .foregroundColor(.primary)
        .fixedSize()
    }
  }
}
