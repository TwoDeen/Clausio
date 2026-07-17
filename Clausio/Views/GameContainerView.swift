//
// GameContainerView.swift
// Clausio
//
// Created by Mohideen Noordeen on 12/06/2026.
// Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
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
struct GameContainerView<LeadingContent: View>: View {
  @ObservedObject var vm: GameViewModel
  let leadingContent: LeadingContent
  
  @State private var speechSynthesizer = AVSpeechSynthesizer()
  
  @State private var completedRows: Set<Int> = []
  @State private var showingPassageSheet = false
  @State private var showingCorpusInfoSheet = false
  
  init(vm: GameViewModel, @ViewBuilder leadingContent: () -> LeadingContent) {
    self.vm = vm
    self.leadingContent = leadingContent()
  }
  
  private var tilesSolvedState: [Bool] {
    vm.tiles.map(\.isSolved)
  }
  
  var body: some View {
    GeometryReader { geometry in
      let hSpacing: CGFloat = vm.isAssistModeOn ? 2 : 8
      
      // Calculate cell width to force equal columns based strictly on available width.
      let availableWidth = geometry.size.width - 32 - (hSpacing * 4)
      let cellWidth = max(0, availableWidth / 5)
      
      // Reduced spacing from 20 to 8 to close the gap between the grid and the controls
      VStack(alignment: .leading, spacing: 8) {
        // Grid Area
        ScrollView(.horizontal, showsIndicators: false) {
          boardGrid(cellWidth: cellWidth)
            .padding(.horizontal, 16)
        }
        .layoutPriority(1)
        
        // Bottom Control Bar
        bottomControlBar
          .padding(.bottom, 8) // Reduced bottom padding
      }
      .padding(.top, 10)
      .frame(width: geometry.size.width, height: geometry.size.height)
      .onChange(of: tilesSolvedState) { _ in
        detectNewlyCompletedRows()
      }
      .sheet(isPresented: $showingPassageSheet) {
        PassageSheetView(
          rows: vm.passageRows,
          plainPassageText: vm.fullPassageText,
          hasFurigana: vm.hasFuriganaPassage,
          sentenceTranslationsById: vm.sentenceTranslationsById
        )
      }
      .sheet(isPresented: $showingCorpusInfoSheet) {
        CorpusInfoSheetView(corpusRef: vm.corpusRef)
      }
    }
  }
  
  @ViewBuilder
  private func boardGrid(cellWidth: CGFloat) -> some View {
    let hSpacing: CGFloat = vm.isAssistModeOn ? 2 : 8
    let vSpacing: CGFloat = vm.isAssistModeOn ? 2 : 10
    
    VStack(spacing: vSpacing) {
      ForEach(0..<5, id: \.self) { row in
        HStack(spacing: hSpacing) {
          ForEach(0..<5, id: \.self) { col in
            let index = (row * 5) + col
            tileCell(at: index)
              .frame(width: cellWidth)
              .frame(maxHeight: .infinity) // Forces equal height for all columns
          }
        }
        .frame(maxHeight: .infinity) // Forces equal height for all rows
      }
    }
    .frame(maxHeight: .infinity) // Stretches grid to fill vertical space evenly
  }
  
  @ViewBuilder
  private func tileCell(at index: Int) -> some View {
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
        useSquareAspectRatio: false,
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
      .lineLimit(2) // Strictly enforce 2 lines maximum
      .environment(\.lineLimit, 2)
      .minimumScaleFactor(0.85) // Allows text to slightly shrink to fit within 2 lines
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
  
  private var bottomControlBar: some View {
    ScrollView(.horizontal, showsIndicators: false) {
      HStack(spacing: 24) {
        
        // Render passed-in injected content (Gamepad/Settings panel)
        if LeadingContent.self != EmptyView.self {
          leadingContent
          
          Divider()
            .frame(height: 24)
        }
        
        // Left-most buttons (Mode Toggles)
        HStack(spacing: 12) {
          modeIconToggle(icon: "puzzlepiece.extension.fill", isOn: $vm.isAssistModeOn)
          modeIconToggle(icon: "brain.head.profile", isOn: $vm.isLearnModeOn)
        }
        
        Divider()
          .frame(height: 24)
        
        // Right-most buttons, immediately to the right
        HStack(spacing: 24) {
          toolbarButton(systemName: "shuffle") {
            withAnimation(.easeInOut) {
              vm.shuffleIncorrectTiles()
            }
          }
          
          toolbarButton(systemName: "arrow.clockwise.circle.fill") {
            withAnimation(.easeInOut) {
              vm.startNewGame()
            }
          }
          
          toolbarButton(systemName: "flag.fill") {
            withAnimation(.spring()) {
              vm.revealSolution()
            }
          }
          
          toolbarButton(systemName: "doc.text.magnifyingglass") {
            showingPassageSheet = true
          }
          .accessibilityLabel("View entire passage")
          .help("View entire passage")
          
          toolbarButton(systemName: "info.circle") {
            showingCorpusInfoSheet = true
          }
          .accessibilityLabel("View story details")
          .help("View story details")
        }
        
        Spacer(minLength: 0)
      }
      .padding(.horizontal, 16)
    }
  }
  
  private func modeIconToggle(icon: String, isOn: Binding<Bool>) -> some View {
    Button {
      withAnimation(.spring(response: 0.3, dampingFraction: 0.65)) {
        isOn.wrappedValue.toggle()
      }
    } label: {
      Image(systemName: icon)
        .font(.system(size: 20, weight: .medium))
        .frame(width: 44, height: 44)
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
  
  private func toolbarButton(systemName: String, action: @escaping () -> Void) -> some View {
    Button(action: action) {
      Image(systemName: systemName)
        .font(.system(size: 24, weight: .medium))
        .foregroundColor(.blue)
        .frame(width: 44, height: 44)
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

// Support for standard initialization when no injected content is provided
extension GameContainerView where LeadingContent == EmptyView {
  init(vm: GameViewModel) {
    self.init(vm: vm, leadingContent: { EmptyView() })
  }
}

// MARK: - Passage Sheet
struct PassageSheetView: View {
  let rows: [[Tile]]
  let plainPassageText: String
  let hasFurigana: Bool
  let sentenceTranslationsById: [Int: String]
  
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
            VStack(alignment: .leading, spacing: 18) {
              ForEach(Array(rows.enumerated()), id: \.offset) { index, row in
                VStack(alignment: .leading, spacing: 8) {
                  RubyRowView(tokens: row)
                  
                  if let translation = sentenceTranslationsById[index + 1],
                     !translation.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    Text(translation)
                      .font(.subheadline)
                      .foregroundColor(.secondary)
                      .fixedSize(horizontal: false, vertical: true)
                      .textSelection(.enabled)
                  }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
              }
            }
          } else {
            VStack(alignment: .leading, spacing: 18) {
              ForEach(Array(rows.enumerated()), id: \.offset) { index, row in
                VStack(alignment: .leading, spacing: 8) {
                  Text(row.map(\.text).joined())
                    .font(.body)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
                  
                  if let translation = sentenceTranslationsById[index + 1],
                     !translation.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    Text(translation)
                      .font(.subheadline)
                      .foregroundColor(.secondary)
                      .fixedSize(horizontal: false, vertical: true)
                      .textSelection(.enabled)
                  }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
              }
            }
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

// MARK: - Corpus Info Sheet
struct CorpusInfoSheetView: View {
  let corpusRef: GamePayload.CorpusReference?
  @Environment(\.dismiss) private var dismiss
  
  var body: some View {
    NavigationView {
      List {
        infoRow("Copyright", "Tadoku No Hiroba " + (corpusRef?.site_url ?? ""))
        infoRow("Story", "copyright belongs to respective author(s) of the story")
        infoRow("Author", corpusRef?.author)
        infoRow("Title", corpusRef?.title)
        infoRow("Published Date", corpusRef?.article_date)
        infoRow("Extraction Date", corpusRef?.extraction_date_time)
        infoRow("Word Level", corpusRef?.word_level?.description)
        infoRow("Sentence Level", corpusRef?.sentence_level?.description)
        if let value = corpusRef?.link, let url = URL(string: value), !value.isEmpty {
          VStack(alignment: .leading, spacing: 4) {
            Text("Story  Link:").font(.caption).foregroundColor(.secondary)
            Link(value, destination: url)
              .font(.body)
          }
          .padding(.vertical, 4)
        }
      }
      .navigationTitle("Info")
      .navigationBarTitleDisplayMode(.inline)
      .toolbar {
        ToolbarItem(placement: .navigationBarTrailing) {
          Button("X") {
            dismiss()
          }
        }
      }
    }
  }
  
  @ViewBuilder
  private func infoRow(_ label: String, _ value: String?) -> some View {
    if let value = value, !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
      VStack(alignment: .leading, spacing: 4) {
        Text(label)
          .font(.caption)
          .foregroundColor(.secondary)
        
        Text(value)
          .font(.body)
          .textSelection(.enabled)
      }
      .padding(.vertical, 4)
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
