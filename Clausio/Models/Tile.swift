//
//  Tile.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 10/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI


struct Tile: Identifiable, Equatable {
  let id = UUID()
  let text: String
  let furigana: String // <-- Add this property back to resolve line 108
  let originalRowId: Int
  let originalColumnId: Int
  var isSolved: Bool = false
}

