import SwiftUI

struct MainAppCoordinatorView: View {
  @State private var activePuzzle: GamePayload? = nil
  
  var body: some View {
    Group {
      if let puzzle = activePuzzle {
        JapaneseConnectionsAppView(
          payload: puzzle,
          onQuit: {
            withAnimation(.spring()) {
              self.activePuzzle = nil
            }
          }
        )
      } else {
        StorySelectionView(
          onPuzzleLoaded: { loadedPayload in
            withAnimation(.spring()) {
              self.activePuzzle = loadedPayload
            }
          }
        )
      }
    }
  }
}
