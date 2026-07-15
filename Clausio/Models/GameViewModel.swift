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
    @Published var gamePayload: GamePayload? = nil

    private var pristineSolutionOrder: [Tile] = []
    private var initialScrambledState: [Tile] = []

    private var cancellables = Set<AnyCancellable>()

    var sentenceTranslationsById: [Int: String] {
        Dictionary(
            uniqueKeysWithValues: (gamePayload?.sentence_translations ?? []).map {
                ($0.sentence_id, $0.english_translation)
            }
        )
    }

    func loadPuzzleFromPayload(_ payload: GamePayload) {
        self.isLoading = true
        self.errorMessage = nil
        self.gamePayload = payload
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

        for i in 0..<tiles.count {
            self.tiles[i].isSolved = false
        }
    }

    func revealSolution() {
        self.didGiveUp = true
        self.tiles = pristineSolutionOrder

        for i in 0..<tiles.count {
            self.tiles[i].isSolved = true
        }

        self.selectedIndex = nil
    }

    func shuffleIncorrectTiles() {
        guard tiles.count == 25 else { return }

        var newTiles = tiles

        for row in 0..<5 {
            let rowStart = row * 5
            let rowEnd = rowStart + 5

            let solvedTiles = newTiles[rowStart..<rowEnd].filter { $0.isSolved }
            var unsolvedTiles = newTiles[rowStart..<rowEnd].filter { !$0.isSolved }.shuffled()

            var rebuiltRow: [Tile] = []
            for col in 0..<5 {
                let index = rowStart + col
                if newTiles[index].isSolved {
                    if let solved = solvedTiles.first(where: {
                        $0.originalRowId == newTiles[index].originalRowId &&
                        $0.originalColumnId == newTiles[index].originalColumnId
                    }) {
                        rebuiltRow.append(solved)
                    }
                } else {
                    rebuiltRow.append(unsolvedTiles.removeFirst())
                }
            }

            for offset in 0..<5 {
                newTiles[rowStart + offset] = rebuiltRow[offset]
            }
        }

        self.tiles = newTiles
        self.selectedIndex = nil
    }

    func handleTap(at index: Int) {
        guard index < tiles.count else { return }
        guard !tiles[index].isSolved else { return }

        if let selected = selectedIndex {
            if selected == index {
                selectedIndex = nil
                return
            }

            swapTiles(at: selected, and: index)
            selectedIndex = nil
            checkSolvedPositions()
        } else {
            selectedIndex = index
        }
    }

    private func swapTiles(at first: Int, and second: Int) {
        guard first != second else { return }
        guard first < tiles.count, second < tiles.count else { return }
        tiles.swapAt(first, second)
    }

    private func checkSolvedPositions() {
        for index in 0..<tiles.count {
            let expectedRow = (index / 5) + 1
            let expectedColumn = (index % 5) + 1

            tiles[index].isSolved =
                tiles[index].originalRowId == expectedRow &&
                tiles[index].originalColumnId == expectedColumn
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
