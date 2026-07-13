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
  
  @Published var didGiveUp: Bool = false
  @Published var corpusRef: CorpusReference? = nil
  
  private var pristineSolutionOrder: [Tile] = []
  private var initialScrambledState: [Tile] = []
  
  private var cancellables = Set<AnyCancellable>()
  
  func loadPuzzleFromPayload(_ payload: GamePayload) {
    self.isLoading = true
    self.errorMessage = nil
    self.corpusRef = payload.corpus_ref
    self.initializeGameGrid(from: payload.grid_matrix)
    self.isLoading = false
  }
  
  private func initializeGameGrid(from remoteMatrix: [ClauseNode]) {
    let processedTiles = remoteMatrix.map { item in
      Tile(
        text: item.clause_text,
        furigana: item.furigana,
        originalRowId: item.grid_coordinates.row,
        originalColumnId: item.grid_coordinates.column,
        sentenceIndividualGrammarLevel: item.sentence_individual_grammar_level
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
    self.didGiveUp = false
    self.tiles = initialScrambledState
    self.selectedIndex = nil
    for i in 0..<self.tiles.count {
      self.tiles[i].isSolved = false
    }
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
      
      let matchesRowIdentity = rowTiles.allSatisfy {
        $0.originalRowId == referenceRowId && !$0.isSolved
      }
      
      if matchesRowIdentity {
        let isOrderedCorrectly = (0..<4).allSatisfy { idx in
          rowTiles[idx].originalColumnId < rowTiles[idx + 1].originalColumnId
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
    self.didGiveUp = true
    self.selectedIndex = nil
    self.tiles = pristineSolutionOrder
    for i in 0..<self.tiles.count {
      self.tiles[i].isSolved = true
    }
  }
  
  // MARK: - Passage Helpers
  
  func solutionTilesForRow(_ row: Int) -> [Tile] {
    pristineSolutionOrder
      .filter { $0.originalRowId == row + 1 }
      .sorted { $0.originalColumnId < $1.originalColumnId }
  }
  
  func fullSentenceForRow(_ row: Int) -> String {
    solutionTilesForRow(row).map(\.text).joined()
  }
  
  func furiganaSentenceForRow(_ row: Int) -> String {
    solutionTilesForRow(row).map { tile in
      let reading = tile.furigana.trimmingCharacters(in: .whitespacesAndNewlines)
      return reading.isEmpty ? tile.text : reading
    }.joined()
  }
  
  var fullPassageText: String {
    (0..<5)
      .map { fullSentenceForRow($0) }
      .filter { !$0.isEmpty }
      .joined(separator: "\n\n")
  }
  
  var fullPassageFuriganaText: String {
    (0..<5)
      .map { furiganaSentenceForRow($0) }
      .filter { !$0.isEmpty }
      .joined(separator: "\n\n")
  }
  
  var hasFuriganaPassage: Bool {
    pristineSolutionOrder.contains {
      !$0.furigana.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty &&
      $0.furigana != $0.text
    }
  }
  
  var passageRows: [[Tile]] {
    (0..<5)
      .map { solutionTilesForRow($0) }
      .filter { !$0.isEmpty }
  }
  
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
