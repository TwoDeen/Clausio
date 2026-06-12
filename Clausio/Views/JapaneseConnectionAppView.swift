import SwiftUI

// MARK: - Main Application Tab Router
struct JapaneseConnectionsAppView: View {
  @StateObject private var vm = GameViewModel()
  
  // 🔑 INJECT DEPENDENCIES
  let payload: GamePayload
  var onQuit: () -> Void
  
  var body: some View {
    TabView {
      ZStack {
        GameContainerView(vm: vm)
          .disabled(vm.isLoading)
        
        // ⏳ THE DYNAMIC HOURGLASS / LOADING OVERLAY
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
        
        // ⚠️ Error visualizer banner
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
      // ❌ DELETED: .task { vm.loadDynamicPuzzle(forLevel: "N4") } is gone!
      .onAppear {
        // ⚡️ Hydrate the view model instantly with the chosen cache data
        vm.loadPuzzleFromPayload(payload)
      }
      
      // 🔑 Pass the quit exit closure straight to settings
      SettingsView(vm: vm, onQuit: onQuit)
        .tabItem {
          Label("Settings", systemImage: "gearshape.fill")
        }
    }
  }
}
