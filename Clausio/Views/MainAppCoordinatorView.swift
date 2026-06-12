//
//  MainAppCoordinatorView.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 12/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//


import SwiftUI

struct MainAppCoordinatorView: View {
    @State private var activePuzzle: GamePayload? = nil
    
    var body: some View {
        if let puzzle = activePuzzle {
            // If a puzzle payload is loaded, pass it to the App Tab Router
            JapaneseConnectionsAppView(payload: puzzle, onQuit: {
                withAnimation(.spring()) {
                    self.activePuzzle = nil // Evicts payload and snaps back to dashboard safely
                }
            })
        } else {
            // Otherwise, render the story discover sheet list
            StorySelectionView(onPuzzleLoaded: { loadedPayload in
                withAnimation(.spring()) {
                    self.activePuzzle = loadedPayload
                }
            })
        }
    }
}