//
//  ClauseNode.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 12/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//


struct ClauseNode: Identifiable, Decodable {
    var id: Int { clause_id }
    let clause_id: Int
    let grid_coordinates: GridCoordinates
    let parent_sentence_id: Int
    let clause_text: String
    let furigana: String
    let sentence_individual_grammar_level: String?  // ← add this
}
