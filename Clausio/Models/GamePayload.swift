//
//  GamePayload.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 12/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

// MARK: - Game Engine Matrix Payload
struct GamePayload: Decodable {
  let target_level_requested: String
  let passage_extraction_strategy: String?
  let total_grid_clauses: Int
  let puzzle_solution_flow: SolutionFlow
  let grid_matrix: [ClauseNode]
  let corpus_ref: CorpusReference?
}

// MARK: - Optional corpus/source metadata
struct CorpusReference: Decodable {
  let source: String?
  let topic_id: String?
  let title: String?
  let link: String?
  let file_path: String?
}
