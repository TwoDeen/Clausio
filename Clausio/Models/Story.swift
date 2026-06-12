//
//  Story.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 12/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import Foundation
// MARK: - API Discovery Models
struct Story: Identifiable, Decodable {
    var id: String { relative_path }
    let name: String
    let relative_path: String
}
