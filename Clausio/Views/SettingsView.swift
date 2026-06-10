//
//  SettingsView.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 10/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI

// MARK: - Settings Screen Component
struct SettingsView: View {
  @ObservedObject var vm: GameViewModel
  
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
      }
      .navigationTitle("Settings")
    }
  }
}
