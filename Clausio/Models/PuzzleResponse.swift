import Foundation

// MARK: - Legacy Network Response Bridge
/// This structure matches the JSON object structure returned by the FastAPI puzzle engine.
struct PuzzleResponse: Decodable {
  let targetLevelRequested: String
  let totalGridClauses: Int
  let gridMatrix: [ClauseNode] // Binds directly to the validated 5x5 data schema
  
  enum CodingKeys: String, CodingKey {
    case targetLevelRequested = "target_level_requested"
    case totalGridClauses = "total_grid_clauses"
    case gridMatrix = "grid_matrix"
  }
}
