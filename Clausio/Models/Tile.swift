//
//  Tile.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 10/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI

// MARK: - Models
struct Tile: Identifiable, Equatable {
  let id = UUID()
  let text: String       // Kanji/Japanese text
  let furigana: String   // Reading helper
  let english: String    // English meaning
  let categoryId: Int    // Group alignment (1 to 5)
  var isSolved: Bool = false
  var correctIndex: Int = 0
}

