import SwiftUI
import Combine

// MARK: - Game View Model
class GameViewModel: ObservableObject {
  @Published var tiles: [Tile] = []
  @Published var selectedIndex: Int? = nil
  @Published var isLoading: Bool = false
  @Published var errorMessage: String? = nil
  
  @Published var isAssistModeOn: Bool = false
  @Published var isLearnModeOn: Bool = false
  
  // 🚀 NEW: Tracks if the user aborted/gave up
  @Published var didGiveUp: Bool = false
  
  private var pristineSolutionOrder: [Tile] = []
  private var initialScrambledState: [Tile] = []
  
  private var cancellables = Set<AnyCancellable>()
  
  func loadPuzzleFromPayload(_ payload: GamePayload) {
    self.isLoading = true
    self.errorMessage = nil
    self.initializeGameGrid(from: payload.grid_matrix)
    self.isLoading = false
  }
  
  private func initializeGameGrid(from remoteMatrix: [ClauseNode]) {
    let processedTiles = remoteMatrix.map { item in
      Tile(
        text: item.clause_text,
        furigana: item.furigana,
        originalRowId: item.grid_coordinates.row,
        originalColumnId: item.grid_coordinates.column
      )
    }
    
    self.pristineSolutionOrder = processedTiles.sorted {
      if $0.originalRowId == $1.originalRowId {
        return $0.originalColumnId < $1.originalColumnId
      }
      return $0.originalRowId < $1.originalRowId
    }
    
    self.tiles = rowPreservedShuffle(processedTiles)
    self.initialScrambledState = self.tiles
    self.selectedIndex = nil
  }
  
  func startNewGame() {
    self.didGiveUp = false // 🚀 Reset the flag on replay
    self.tiles = initialScrambledState
    self.selectedIndex = nil
    for i in 0..<self.tiles.count { self.tiles[i].isSolved = false }
  }
  
  private func rowPreservedShuffle(_ inputTiles: [Tile]) -> [Tile] {
    var shuffled: [Tile] = []
    guard inputTiles.count == 25 else { return inputTiles.shuffled() }
    
    for row in 0..<5 {
      let start = row * 5
      let end = start + 5
      var rowTiles = Array(inputTiles[start..<end])
      rowTiles.shuffle()
      shuffled.append(contentsOf: rowTiles)
    }
    return shuffled
  }
  
  func shuffleIncorrectTiles() {
    self.selectedIndex = nil
    var newTiles = self.tiles
    guard newTiles.count == 25 else { return }
    
    for row in 0..<5 {
      let start = row * 5
      let end = start + 5
      let rowUnsolvedIndices = (start..<end).filter { !newTiles[$0].isSolved }
      let shuffledRowTiles = rowUnsolvedIndices.map { newTiles[$0] }.shuffled()
      
      for (index, originalIndex) in rowUnsolvedIndices.enumerated() {
        newTiles[originalIndex] = shuffledRowTiles[index]
      }
    }
    self.tiles = newTiles
  }
  
  func handleTap(at index: Int) {
    if let selected = selectedIndex {
      if selected == index {
        selectedIndex = nil
      } else {
        let selectedRow = selected / 5
        let targetRow = index / 5
        
        if selectedRow != targetRow {
          selectedIndex = index
          return
        }
        
        if tiles[index].isSolved || tiles[selected].isSolved {
          selectedIndex = index
        } else {
          tiles.swapAt(selected, index)
          selectedIndex = nil
          checkForSolvedRows()
        }
      }
    } else {
      selectedIndex = index
    }
  }
  
  private func checkForSolvedRows() {
    for row in 0..<5 {
      let start = row * 5
      let end = start + 5
      let rowTiles = Array(tiles[start..<end])
      let referenceRowId = rowTiles.first?.originalRowId
      
      let matchesRowIdentity = rowTiles.allSatisfy { $0.originalRowId == referenceRowId && !$0.isSolved }
      
      if matchesRowIdentity {
        let isOrderedCorrectly = (0..<4).allSatisfy { idx in
          rowTiles[idx].originalColumnId < rowTiles[idx+1].originalColumnId
        }
        if isOrderedCorrectly {
          for index in start..<end {
            tiles[index].isSolved = true
          }
        }
      }
    }
  }
  
  func revealSolution() {
    self.didGiveUp = true // 🚀 Tell the app the user aborted/gave up!
    self.selectedIndex = nil
    self.tiles = pristineSolutionOrder
    for i in 0..<self.tiles.count {
      self.tiles[i].isSolved = true
    }
  }
  
//  pastelSakura = Color(red: 0.98, green: 0.89, blue: 0.91)
//  static let pastelMatcha = Color(red: 0.82, green: 0.90, blue: 0.73)
//  static let pastelMomo = Color(red: 1.00, green: 0.85, blue: 0.80)
//  static let pastelAsagi = Color(red: 0.75, green: 0.89, blue: 0.97)
//  static let pastelKobai = Color(red: 0.95, green: 0.83, blue: 0.93)
//  static let pastelShironeri = Color(red: 0.98, green: 0.97, blue: 0.94)
//  static let pastelYamabuki = Color(red: 0.98, green: 0.89, blue: 0.56)

  
  func colorForCategory(_ originalRowId: Int) -> Color {
    switch originalRowId {
      case 1: return .pastelSakura
      case 2: return .pastelMatcha
      case 3: return .pastelAsagi
      case 4: return .pastelKobai
      case 5: return .pastelMomo
      default: return .pastelShironeri
    }
  }
}
