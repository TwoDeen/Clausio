struct GridClause: Codable {
  let clauseId: Int
  let gridCoordinates: GridCoordinate
  let parentSentenceId: Int
  let clauseText: String
  let furigana: String? // <-- Add this network tracking field
  
  enum CodingKeys: String, CodingKey {
    case clauseId = "clause_id"
    case gridCoordinates = "grid_coordinates"
    case parentSentenceId = "parent_sentence_id"
    case clauseText = "clause_text"
    case furigana
  }
}
