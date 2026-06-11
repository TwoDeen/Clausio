import SwiftUI



// MARK: - Main Application Tab Router
struct JapaneseConnectionsAppView: View {
  @StateObject private var vm = GameViewModel()
  
  var body: some View {
    TabView {
      GameContainerView(vm: vm)
        .tabItem {
          Label("Play", systemImage: "gamecontroller.fill")
        }
      // 🔄 CHANGED: .task handles background compilation scheduling perfectly on macOS
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

