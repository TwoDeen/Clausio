//
//  Item.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 10/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import Foundation
import SwiftData

@Model
final class Item {
    var timestamp: Date
    
    init(timestamp: Date) {
        self.timestamp = timestamp
    }
}
