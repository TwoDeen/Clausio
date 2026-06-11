// MARK: - API Struct Models
struct PuzzleResponse: Codable {
  let targetLevelRequested: String
  let passageExtractionStrategy: String
  let totalGridClauses: Int
  let gridMatrix: [GridClause]
  
  enum CodingKeys: String, CodingKey {
    case targetLevelRequested = "target_level_requested"
    case passageExtractionStrategy = "passage_extraction_strategy"
    case totalGridClauses = "total_grid_clauses"
    case gridMatrix = "grid_matrix"
  }
}
