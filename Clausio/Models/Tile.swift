//
//  Tile.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 10/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import Foundation

struct Tile: Identifiable, Codable {
  // Unique identifier required by SwiftUI for ForEach loops
  var id = UUID()
  
  // Core text data
  let text: String
  let furigana: String
  
  // Grid tracking coordinates
  let originalRowId: Int
  let originalColumnId: Int
  
  // 🚀 THE FIX: Converted to standard Swift camelCase
  let sentenceIndividualGrammarLevel: String?
  
  // Live game state
  var isSolved: Bool = false
  
  // MARK: - JSON Mapping Keys
  enum CodingKeys: String, CodingKey {
    case text = "clause_text"
    case furigana = "furigana"
    case gridCoordinates = "grid_coordinates"
    case sentenceIndividualGrammarLevel = "sentence_individual_grammar_level"
  }
  
  // Nested keys to dive into the JSON "grid_coordinates" object
  enum GridCoordinatesKeys: String, CodingKey {
    case row
    case column
  }
  
  // MARK: - Custom Decoder (Reading JSON)
  init(from decoder: Decoder) throws {
    let container = try decoder.container(keyedBy: CodingKeys.self)
    
    // Decode top-level strings
    text = try container.decode(String.self, forKey: .text)
    furigana = try container.decode(String.self, forKey: .furigana)
    
    // 🚀 THE FIX: Use the camelCase coding key
    sentenceIndividualGrammarLevel = try container.decodeIfPresent(String.self, forKey: .sentenceIndividualGrammarLevel)
    
    // Dive into "grid_coordinates" to grab the row and column ints
    let gridContainer = try container.nestedContainer(keyedBy: GridCoordinatesKeys.self, forKey: .gridCoordinates)
    originalRowId = try gridContainer.decode(Int.self, forKey: .row)
    originalColumnId = try gridContainer.decode(Int.self, forKey: .column)
    
    // Initialize default runtime states
    id = UUID()
    isSolved = false
  }
  
  // MARK: - Custom Encoder (Writing JSON)
  func encode(to encoder: Encoder) throws {
    var container = encoder.container(keyedBy: CodingKeys.self)
    
    try container.encode(text, forKey: .text)
    try container.encode(furigana, forKey: .furigana)
    try container.encodeIfPresent(sentenceIndividualGrammarLevel, forKey: .sentenceIndividualGrammarLevel)
    
    var gridContainer = container.nestedContainer(keyedBy: GridCoordinatesKeys.self, forKey: .gridCoordinates)
    try gridContainer.encode(originalRowId, forKey: .row)
    try gridContainer.encode(originalColumnId, forKey: .column)
  }
  
  // MARK: - Manual Initializer
  init(id: UUID = UUID(), text: String, furigana: String = "", originalRowId: Int, originalColumnId: Int, isSolved: Bool = false, sentenceIndividualGrammarLevel: String? = nil) {
    self.id = id
    self.text = text
    self.furigana = furigana
    self.originalRowId = originalRowId
    self.originalColumnId = originalColumnId
    self.isSolved = isSolved
    self.sentenceIndividualGrammarLevel = sentenceIndividualGrammarLevel
  }
}
