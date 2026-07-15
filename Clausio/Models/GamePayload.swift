//
//  GamePayload.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 12/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

struct GamePayload: Decodable {
    let target_level_requested: String
    let passage_extraction_strategy: String?
    let total_grid_clauses: Int
    let puzzle_solution_flow: SolutionFlow
    let grid_matrix: [ClauseNode]
    let corpus_ref: CorpusReference?
    let sentence_translations: [SentenceTranslation]?

    struct SentenceTranslation: Decodable {
        let sentence_id: Int
        let japanese: String
        let english_translation: String
    }

    struct CorpusReference: Decodable {
        let source: String?
        let topic_id: String?
        let title: String?
        let link: String?
        let file_path: String?
        let site_url: String?
        let pdf_url: String?
        let author: String?
        let article_date: String?
        let article_type: String?
        let word_level: Int?
        let sentence_level: Int?
        let article_length: Int?
        let extraction_date_time: String?
    }
}
