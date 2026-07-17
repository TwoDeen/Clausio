//
//  JapaneseConnectionsAppView.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 12/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI

// MARK: - Main Application Router
struct JapaneseConnectionsAppView: View {
  @StateObject private var vm = GameViewModel()
  
  let payload: GamePayload
  var onQuit: () -> Void
  
  @State private var showSolvedScreen = false
  @State private var hasLoadedPayload = false
  @State private var selectedTab: AppTab = .play
  
  private var solvedTileCount: Int {
    vm.tiles.filter(\.isSolved).count
  }
  
  var body: some View {
    GeometryReader { geometry in
      let isCompactPhone = geometry.size.width < 700
      
      Group {
        if isCompactPhone {
          compactLayout
        } else {
          sideRailLayout(isCompactPhone: isCompactPhone)
        }
      }
      .frame(maxWidth: .infinity, maxHeight: .infinity)
      .background(Color.clear)
      .onAppear {
        guard !hasLoadedPayload else { return }
        hasLoadedPayload = true
        vm.loadPuzzleFromPayload(payload)
      }
      .onChange(of: solvedTileCount) { count in
        if count == 25 && !vm.tiles.isEmpty && !vm.didGiveUp {
          DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
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
            selectedTab = .play
            vm.startNewGame()
          },
          onNextStory: {
            showSolvedScreen = false
            selectedTab = .play
            onQuit()
          }
        )
      }
    }
  }
  
  private var compactLayout: some View {
    ZStack(alignment: .bottom) {
      currentContent(isCompactPhone: true)
        .padding(.top, 12)
        .padding(.bottom, 72)
      
      bottomCompactBar
        .padding(.bottom, 10)
        .padding(.horizontal, 16)
    }
    .ignoresSafeArea(.keyboard, edges: .bottom)
  }
  
  private func sideRailLayout(isCompactPhone: Bool) -> some View {
    currentContent(isCompactPhone: isCompactPhone)
      .padding(.top, 18)
      .padding(.bottom, 8) // Reduced bottom padding here
  }
  
  @ViewBuilder
  private func currentContent(isCompactPhone: Bool) -> some View {
    switch selectedTab {
      case .play:
        ZStack {
          // Pass the bottomCompactBar into GameContainerView if NOT in compact mode
          GameContainerView(vm: vm) {
            if !isCompactPhone {
              bottomCompactBar
            }
          }
          .disabled(vm.isLoading)
          
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
          
          if let errorMessage = vm.errorMessage {
            VStack {
              Text(errorMessage)
                .foregroundColor(.white)
                .padding()
                .background(
                  RoundedRectangle(cornerRadius: 10)
                    .fill(Color.red)
                )
                .padding()
              Spacer()
            }
          }
        }
        
      case .settings:
        SettingsView(vm: vm, onQuit: onQuit)
    }
  }
  
  private var bottomCompactBar: some View {
    HStack(spacing: 8) {
      tabButton(for: .play, systemImage: "gamecontroller.fill")
      tabButton(for: .settings, systemImage: "gearshape.fill")
    }
    .padding(.horizontal, 10)
    .padding(.vertical, 8)
    .background(
      Capsule(style: .continuous)
        .fill(.ultraThinMaterial)
    )
    .overlay(
      Capsule(style: .continuous)
        .stroke(Color.primary.opacity(0.08), lineWidth: 1)
    )
    .shadow(color: Color.black.opacity(0.08), radius: 12, x: 0, y: 4)
  }
  
  private func tabButton(for tab: AppTab, systemImage: String) -> some View {
    Button {
      withAnimation(.spring(response: 0.25, dampingFraction: 0.85)) {
        selectedTab = tab
      }
    } label: {
      Image(systemName: systemImage)
        .font(.system(size: 18, weight: .semibold))
        .foregroundColor(selectedTab == tab ? .accentColor : .secondary)
        .frame(width: 54, height: 38)
        .background(
          Capsule(style: .continuous)
            .fill(
              selectedTab == tab
              ? Color.accentColor.opacity(0.14)
              : Color.clear
            )
        )
        .overlay(
          Capsule(style: .continuous)
            .stroke(
              selectedTab == tab
              ? Color.accentColor.opacity(0.20)
              : Color.clear,
              lineWidth: 1
            )
        )
    }
    .buttonStyle(.plain)
    .accessibilityLabel(tab.title)
    .help(tab.title)
  }
}

// MARK: - Supporting Types
private enum AppTab: Hashable {
  case play
  case settings
  
  var title: String {
    switch self {
      case .play:
        return "Play"
      case .settings:
        return "Settings"
    }
  }
}
