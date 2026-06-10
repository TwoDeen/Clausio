//
//  GameViewModel.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 10/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI
import Combine

// MARK: - Game View Model
class GameViewModel: ObservableObject {
  @Published var tiles: [Tile] = []
  @Published var selectedIndex: Int? = nil
  
  // Settings synced across views
  @Published var isAssistModeOn: Bool = false
  @Published var isLearnModeOn: Bool = false
  
  init() {
    startNewGame()
  }
  
  // Cleaned Mock Data: Exactly 25 tiles (5 per category)
  private let mockData: [Tile] = [
    // Cat 1: Simple Action (Yellow)
    Tile(text: "お姉ちゃんは", furigana: "おねえちゃんは", english: "Older sister (topic)", categoryId: 1),
    Tile(text: "今日", furigana: "きょう", english: "Today", categoryId: 1),
    Tile(text: "スーパーで", furigana: "すーぱーで", english: "At the supermarket", categoryId: 1),
    Tile(text: "ラーメンを", furigana: "らーめんを", english: "Ramen (object)", categoryId: 1),
    Tile(text: "食べました", furigana: "たべました", english: "Ate (past)", categoryId: 1),
    
    // Cat 2: Travel & Motion (Green)
    Tile(text: "友達は", furigana: "ともだちは", english: "Friend (topic)", categoryId: 2),
    Tile(text: "来週", furigana: "らいしゅう", english: "Next week", categoryId: 2),
    Tile(text: "東京に", furigana: "とうきょうに", english: "To Tokyo", categoryId: 2),
    Tile(text: "新幹線で", furigana: "しんかんせんで", english: "By Shinkansen", categoryId: 2),
    Tile(text: "行きます", furigana: "いきます", english: "Will go", categoryId: 2),
    
    // Cat 3: Target of Desire (Blue)
    Tile(text: "私は", furigana: "わたしは", english: "I (topic)", categoryId: 3),
    Tile(text: "週末に", furigana: "しゅうまつに", english: "On the weekend", categoryId: 3),
    Tile(text: "古い映画を", furigana: "ふるいえいがを", english: "Old movie (object)", categoryId: 3),
    Tile(text: "家で", furigana: "いえで", english: "At home", categoryId: 3),
    Tile(text: "見たいです", furigana: "みたいです", english: "Want to watch", categoryId: 3),
    
    // Cat 4: Complex Objects (Purple)
    Tile(text: "田中さんは", furigana: "たなかさんは", english: "Mr. Tanaka (topic)", categoryId: 4),
    Tile(text: "いっしょに", furigana: "いっしょに", english: "Together", categoryId: 4),
    Tile(text: "リンゴと", furigana: "りんごと", english: "Apples and...", categoryId: 4),
    Tile(text: "バナナを", furigana: "ばななを", english: "Bananas (object)", categoryId: 4),
    Tile(text: "買いました", furigana: "かいました", english: "Bought", categoryId: 4),
    
    // Cat 5: Static Existence (Orange)
    Tile(text: "七時に", furigana: "しちじに", english: "At 7 o'clock", categoryId: 5),
    Tile(text: "猫が", furigana: "ねこが", english: "Cat (subject)", categoryId: 5),
    Tile(text: "部屋に", furigana: "へやに", english: "In the room", categoryId: 5),
    Tile(text: "椅子の上に", furigana: "いすのうえに", english: "On top of the chair", categoryId: 5),
    Tile(text: "います", furigana: "います", english: "There is/exists", categoryId: 5)
  ]
  
  func startNewGame() {
    tiles = mockData.shuffled()
    selectedIndex = nil
  }
  
  func abortGame() {
    tiles.shuffle()
    for i in 0..<tiles.count { tiles[i].isSolved = false }
    selectedIndex = nil
  }
  
  func shuffleIncorrectTiles() {
    selectedIndex = nil
    let unsolvedIndices = tiles.indices.filter { !tiles[$0].isSolved }
    let unsolvedTiles = unsolvedIndices.map { tiles[$0] }.shuffled()
    
    for (index, originalIndex) in unsolvedIndices.enumerated() {
      tiles[originalIndex] = unsolvedTiles[index]
    }
  }
  
  func handleTap(at index: Int) {
    if let selected = selectedIndex {
      if selected == index {
        // Tapping the same tile toggles it off
        selectedIndex = nil
      } else {
        // SMART SAFEGUARD: If either the previously selected tile OR the newly tapped tile
        // is solved (e.g. SolutionMode is active), do not swap them. Instead, shift selection focus.
        if tiles[index].isSolved || tiles[selected].isSolved {
          selectedIndex = index
        } else {
          // Both tiles are active/unsolved -> safe to perform game mechanics swap
          tiles.swapAt(selected, index)
          selectedIndex = nil
          checkForSolvedRows()
        }
      }
    } else {
      // No prior selection -> highlight the tile
      selectedIndex = index
    }
  }
  
  private func checkForSolvedRows() {
    for row in 0..<5 {
      let start = row * 5
      let end = start + 5
      let rowTiles = tiles[start..<end]
      
      let firstCat = rowTiles.first?.categoryId
      let isRowUnified = rowTiles.allSatisfy { $0.categoryId == firstCat && !$0.isSolved }
      
      if isRowUnified {
        for index in start..<end {
          tiles[index].isSolved = true
        }
      }
    }
  }
    
  func revealSolution() {
    selectedIndex = nil
    // Reset tiles to the original pristine mockData array order
    tiles = mockData
    // Mark every tile as solved to trigger the color-coded rows
    for i in 0..<tiles.count {
      tiles[i].isSolved = true
    }
  }
  
  func colorForCategory(_ id: Int) -> Color {
    switch id {
      case 1: return .yellow
      case 2: return .green
      case 3: return .blue
      case 4: return .purple
      case 5: return .orange
      default: return .gray
    }
  }
}
