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
          sideRailLayout
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
      currentContent
        .padding(.top, 12)
        .padding(.bottom, 72)
      
      bottomCompactBar
        .padding(.bottom, 10)
        .padding(.horizontal, 16)
    }
    .ignoresSafeArea(.keyboard, edges: .bottom)
  }
  
  private var sideRailLayout: some View {
    HStack(spacing: 16) {
      leftVerticalTabRail
        .padding(.leading, 12)
        .padding(.top, 18)
        .padding(.bottom, 18)
      
      currentContent
        .padding(.trailing, 12)
        .padding(.top, 18)
        .padding(.bottom, 18)
    }
  }
  
  @ViewBuilder
  private var currentContent: some View {
    switch selectedTab {
      case .play:
        ZStack {
          GameContainerView(vm: vm)
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
  
  private var leftVerticalTabRail: some View {
    VStack(spacing: 10) {
      verticalTabButton(for: .play, systemImage: "gamecontroller.fill")
      verticalTabButton(for: .settings, systemImage: "gearshape.fill")
    }
    .padding(.horizontal, 8)
    .padding(.vertical, 10)
    .background(
      RoundedRectangle(cornerRadius: 22, style: .continuous)
        .fill(.ultraThinMaterial)
    )
    .overlay(
      RoundedRectangle(cornerRadius: 22, style: .continuous)
        .stroke(Color.primary.opacity(0.08), lineWidth: 1)
    )
    .shadow(color: Color.black.opacity(0.06), radius: 10, x: 0, y: 3)
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
  
  private func verticalTabButton(for tab: AppTab, systemImage: String) -> some View {
    Button {
      withAnimation(.spring(response: 0.25, dampingFraction: 0.85)) {
        selectedTab = tab
      }
    } label: {
      Image(systemName: systemImage)
        .font(.system(size: 18, weight: .semibold))
        .foregroundColor(selectedTab == tab ? .accentColor : .secondary)
        .frame(width: 42, height: 42)
        .background(
          RoundedRectangle(cornerRadius: 14, style: .continuous)
            .fill(
              selectedTab == tab
              ? Color.accentColor.opacity(0.14)
              : Color.clear
            )
        )
        .overlay(
          RoundedRectangle(cornerRadius: 14, style: .continuous)
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
