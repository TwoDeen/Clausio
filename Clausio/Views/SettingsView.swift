import SwiftUI

// MARK: - Settings Screen Component
struct SettingsView: View {
  @ObservedObject var vm: GameViewModel
  var onQuit: () -> Void // 🔑 Linked up to coordinator tracking states
  
  var body: some View {
    NavigationView {
      Form {
        Section(header: Text("Gameplay Assists")) {
          Toggle(isOn: $vm.isAssistModeOn) {
            VStack(alignment: .leading, spacing: 4) {
              Text("Assist Mode")
              Text("Attaches tiles closer together structurally.")
                .font(.caption)
                .foregroundColor(.secondary)
            }
          }
          
          Toggle(isOn: $vm.isLearnModeOn) {
            VStack(alignment: .leading, spacing: 4) {
              Text("Learn Mode")
              Text("Displays Furigana and translations on click.")
                .font(.caption)
                .foregroundColor(.secondary)
            }
          }
        }
        
        // 🚪 ADDED: STORY DISCONNECT NAVIGATION CELL
        Section(header: Text("Story Collection")) {
          Button(role: .destructive, action: {
            onQuit()
          }) {
            HStack {
              Image(systemName: "arrow.left.circle.fill")
              Text("Change Active Story Document")
                .fontWeight(.medium)
            }
          }
        }
      }
      .navigationTitle("Settings")
    }
  }
}
