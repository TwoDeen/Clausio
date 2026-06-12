import SwiftUI



// MARK: - Main Application Tab Router
struct JapaneseConnectionsAppView: View {
  @StateObject private var vm = GameViewModel()
  
  var body: some View {
    TabView {
      // 1. Wrap the Play screen in a coordinate system
      ZStack {
        GameContainerView(vm: vm)
          .disabled(vm.isLoading) // Dim and freeze board interaction during calls
        
        // ⏳ THE DYNAMIC HOURGLASS / LOADING OVERLAY
        if vm.isLoading {
          VStack(spacing: 16) {
            ProgressView()
              .scaleEffect(1.5)
              .progressViewStyle(CircularProgressViewStyle(tint: .accentColor))
            
            Text("Compiling Story Clauses...")
              .font(.headline)
              .foregroundColor(.secondary)
            
            Text("Running GiNZa Deep NLP Analytics Framework")
              .font(.caption)
              .foregroundColor(.gray)
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
          .transition(.opacity.combined(with: .scale))
        }
        
        // ⚠️ OPTIONAL: Error visualizer banner
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
      .task {
        vm.loadDynamicPuzzle(forLevel: "N4")
      }
      
      SettingsView(vm: vm)
        .tabItem {
          Label("Settings", systemImage: "gearshape.fill")
        }
    }
  }
}

// MARK: - Canvas Preview
struct JapaneseConnectionsAppView_Previews: PreviewProvider {
  static var previews: some View {
    JapaneseConnectionsAppView()
  }
}

