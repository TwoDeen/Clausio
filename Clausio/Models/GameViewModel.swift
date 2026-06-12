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
  
  private var pristineSolutionOrder: [Tile] = []
  private var cancellables = Set<AnyCancellable>()
  
  // ❌ DELETED: loadDynamicPuzzle(forLevel:) has been removed because
  // orchestration routing is now handled asynchronously inside StorySelectionView.
  
  // 🔑 NEW: Hydrates the game grid assets instantly via the selection layer payload
  func loadPuzzleFromPayload(_ payload: GamePayload) {
    self.isLoading = true
    self.errorMessage = nil
    
    // Call our initialization handler mapping directly against ClauseNode structures
    self.initializeGameGrid(from: payload.grid_matrix)
    
    self.isLoading = false
  }
  
  // ⚙️ CHANGED: Accepts ClauseNode items parsed natively from the network client pipeline
  private func initializeGameGrid(from remoteMatrix: [ClauseNode]) {
    let processedTiles = remoteMatrix.map { item in
      Tile(
        text: item.clause_text,
        furigana: item.furigana, // 🔄 Transfers server transcription safely
        originalRowId: item.grid_coordinates.row,
        originalColumnId: item.grid_coordinates.column
      )
    }
    
    // Cache the pristine answer solution matrix (Sorted row-by-row, column-by-column)
    self.pristineSolutionOrder = processedTiles.sorted {
      if $0.originalRowId == $1.originalRowId {
        return $0.originalColumnId < $1.originalColumnId
      }
      return $0.originalRowId < $1.originalRowId
    }
    
    // Scramble runtime tile matrix indexes to initiate gameplay
    self.tiles = processedTiles.shuffled()
    self.selectedIndex = nil
  }
  
  func startNewGame() {
    tiles = tiles.shuffled()
    selectedIndex = nil
    for i in 0..<tiles.count { tiles[i].isSolved = false }
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
        selectedIndex = nil
      } else {
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
  
  /// Checks if a row contains 5 matching items placed in correct chronological order (Columns 1-5)
  private func checkForSolvedRows() {
    for row in 0..<5 {
      let start = row * 5
      let end = start + 5
      let rowTiles = Array(tiles[start..<end])
      
      let referenceRowId = rowTiles.first?.originalRowId
      
      // Step 1: Ensure all 5 items belong to the same original sentence row identity
      let matchesRowIdentity = rowTiles.allSatisfy { $0.originalRowId == referenceRowId && !$0.isSolved }
      
      if matchesRowIdentity {
        // Step 2: Verify column sequence flows left-to-right from 1 to 5
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
    selectedIndex = nil
    tiles = pristineSolutionOrder
    for i in 0..<tiles.count {
      tiles[i].isSolved = true
    }
  }
  
  func colorForCategory(_ originalRowId: Int) -> Color {
    switch originalRowId {
      case 1: return .yellow
      case 2: return .green
      case 3: return .blue
      case 4: return .purple
      case 5: return .orange
      default: return .gray
    }
  }
}
