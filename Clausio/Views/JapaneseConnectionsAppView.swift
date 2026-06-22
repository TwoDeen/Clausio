//
//  JapaneseConnectionsAppView.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 12/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI

// MARK: - Main Application Tab Router
struct JapaneseConnectionsAppView: View {
  @StateObject private var vm = GameViewModel()
  
  let payload: GamePayload
  var onQuit: () -> Void
  
  // 🏆 Controls presentation of the post-solve reading screen
  @State private var showSolvedScreen = false
  
  // Derived count observed by onChange — Int is Equatable so diffing is free
  private var solvedTileCount: Int {
    vm.tiles.filter(\.isSolved).count
  }
  
  var body: some View {
    TabView {
      ZStack {
        GameContainerView(vm: vm)
          .disabled(vm.isLoading)
        
        // ⏳ Loading overlay
        if vm.isLoading {
          VStack(spacing: 16) {
            ProgressView()
              .scaleEffect(1.5)
              .progressViewStyle(CircularProgressViewStyle(tint: .accentColor))
            
            Text("Compiling Story Clauses...")
              .font(.headline)
              .foregroundColor(.secondary)
          }
          .padding(30)
          .background(
            RoundedRectangle(cornerRadius: 16)
            #if os(macOS)
              .fill(Color(NSColor.windowBackgroundColor))
            #else
              .fill(Color(UIColor.systemBackground))
            #endif
              .shadow(color: Color.black.opacity(0.15), radius: 10)
          )
        }
        
        // ⚠️ Error banner
        if let errorMessage = vm.errorMessage {
          VStack {
            Text(errorMessage)
              .foregroundColor(.white)
              .padding()
              .background(RoundedRectangle(cornerRadius: 10).fill(Color.red))
              .padding()
            Spacer()
          }
        }
      }
      .tabItem {
        Label("Play", systemImage: "gamecontroller.fill")
      }
      .onAppear {
        vm.loadPuzzleFromPayload(payload)
      }
      // 🏆 Detect full board completion and present the reading screen
      .onChange(of: solvedTileCount) { count in
        
        // 🚀 THE FIX: Only navigate to the next screen if they actually solved it themselves!
        if count == 25 && !vm.tiles.isEmpty && !vm.didGiveUp {
          
          // Delay lets the final row's solve animation play before transitioning
          DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
            // Guard: re-check in case the user restarted during the delay
            if vm.tiles.filter(\.isSolved).count == 25 && !vm.didGiveUp {
              showSolvedScreen = true
            }
          }
        }
      }
      .adaptiveFullScreenCover(isPresented: $showSolvedScreen) {
        SolvedReadingView(
          vm: vm,
          onPlayAgain: {
            showSolvedScreen = false
            vm.startNewGame()
          },
          onNextStory: {
            showSolvedScreen = false
            onQuit()                       // Pops back to StorySelectionView
          }
        )
      }
      
      SettingsView(vm: vm, onQuit: onQuit)
        .tabItem {
          Label("Settings", systemImage: "gearshape.fill")
        }
    }
  }
}
