//
//  StorySelectionView.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 12/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//


import SwiftUI

struct StorySelectionView: View {
    // --- STATE MANAGEMENT ---
    @State private var stories: [Story] = []
    @State private var selectedLevel = "N4"
    @State private var isLoading = false
    @State private var errorMessage: String? = nil
    
    // --- ENVIRONMENT DEFINITIONS ---
    let levels = ["N5", "N4", "N3", "N2", "N1"]
    //let backendURL = "http://localhost:8000" // Adjust to your production cluster IP when deploying
  // 🔑 NEW: Replace with your Mac's actual local network IP address
    let backendURL = "http://192.168.1.126:8000" // <-- Put your IP here!
    
    // Callback action passing the configured payload up to your parent App view router
    var onPuzzleLoaded: (GamePayload) -> Void 
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // JLPT Difficulty Selector
                VStack(alignment: .leading, spacing: 8) {
                    Text("Target Difficulty Level")
                        .font(.caption)
                        .fontWeight(.bold)
                        .foregroundColor(.secondary)
                        .padding(.horizontal)
                    
                    Picker("Select Difficulty", selection: $selectedLevel) {
                        ForEach(levels, id: \.self) { level in
                            Text(level).tag(level)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)
                    .padding(.bottom, 12)
                }
                .background(Color.platformGroupedBackground)
                Divider()
                
                // Error Notification Banner
                if let error = errorMessage {
                    HStack {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.red)
                        Text(error)
                            .font(.subheadline)
                            .foregroundColor(.primary)
                    }
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(Color.red.opacity(0.1))
                }
                
                // Content Switcher based on Active Engine Connection States
                if isLoading {
                    Spacer()
                    VStack(spacing: 16) {
                        ProgressView()
                            .scaleEffect(1.5)
                        Text("Parsing Japanese Text...")
                            .font(.headline)
                            .foregroundColor(.secondary)
                        Text("GiNZa is compiling grammatical dependencies.")
                            .font(.caption)
                            .foregroundColor(.gray)
                    }
                    Spacer()
                } else {
                    List(stories) { story in
                        Button(action: {
                            generateAndLoadPuzzle(for: story)
                        }) {
                            HStack(spacing: 16) {
                                Image(systemName: "book.closed.fill")
                                    .font(.title2)
                                    .foregroundColor(.accentColor)
                                    .frame(width: 40, height: 40)
                                    .background(Color.accentColor.opacity(0.1))
                                    .cornerRadius(8)
                                
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(story.name)
                                        .font(.headline)
                                        .foregroundColor(.primary)
                                    Text(story.relative_path)
                                        .font(.caption2)
                                        .lineLimit(1)
                                        .foregroundColor(.secondary)
                                }
                                
                                Spacer()
                                
                                Image(systemName: "chevron.right")
                                    .font(.caption)
                                    .foregroundColor(.gray)
                            }
                            .padding(.vertical, 4)
                        }
                    }
                    .adaptiveListStyle()
                    .refreshable {
                        fetchStoryList()
                    }
                }
            }
            .navigationTitle("Clausio Stories")
            .onAppear(perform: fetchStoryList)
        }
    }
    
    // --- SERVICE FUNCTIONS (API LAYER) ---
    
    /// Scans backend directory tree for pre-tagged reading documents
    func fetchStoryList() {
        guard let url = URL(string: "\(backendURL)/api/stories") else { return }
        errorMessage = nil
        
        URLSession.shared.dataTask(with: url) { data, response, error in
            if let error = error {
                DispatchQueue.main.async {
                    self.errorMessage = "Connection failed: \(error.localizedDescription)"
                }
                return
            }
            
            guard let data = data else { return }
            
            do {
                let decoded = try JSONDecoder().decode([String: [Story]].self, from: data)
                DispatchQueue.main.async {
                    self.stories = decoded["stories"] ?? []
                }
            } catch {
                DispatchQueue.main.async {
                    self.errorMessage = "Failed parsing available story manifest files."
                }
            }
        }.resume()
    }
    
    /// Requests the puzzle matrix configuration from the server (Instant load on Cache Hit)
    func generateAndLoadPuzzle(for story: Story) {
        guard let url = URL(string: "\(backendURL)/api/puzzle/generate") else { return }
        
        withAnimation {
            isLoading = true
            errorMessage = nil
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Match the exact field property keys that Pydantic models expect on backend endpoints
        let bodyPayload: [String: String] = [
            "file_path": story.relative_path,
            "level": selectedLevel
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: bodyPayload)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            DispatchQueue.main.async {
                withAnimation { self.isLoading = false }
            }
            
            if let error = error {
                DispatchQueue.main.async {
                    self.errorMessage = "Network error: \(error.localizedDescription)"
                }
                return
            }
            
            guard let data = data else { return }
            
            // Check for explicit backend 404/500 HTTP failures safely
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode != 200 {
                DispatchQueue.main.async {
                    self.errorMessage = "Server generation error (\(httpResponse.statusCode))."
                }
                return
            }
            
            do {
                let gamePayload = try JSONDecoder().decode(GamePayload.self, from: data)
                DispatchQueue.main.async {
                    // Hand off the payload to the main app layout view to play the level instantly!
                    self.onPuzzleLoaded(gamePayload)
                }
            } catch let jsonError {
                print("JSON Parsing Failure details: \(jsonError)")
                DispatchQueue.main.async {
                    self.errorMessage = "Puzzle data validation schema failed mapping check."
                }
            }
        }.resume()
    }
}

extension Color {
  static var platformGroupedBackground: Color {
#if os(macOS)
    return Color(NSColor.windowBackgroundColor)
#else
    return Color(UIColor.systemGroupedBackground)
#endif
  }
}

// MARK: - Cross-Platform List Style
struct AdaptiveListStyleModifier: ViewModifier {
  func body(content: Content) -> some View {
#if os(iOS)
    content.listStyle(.insetGrouped)
#else
    content.listStyle(.inset)
#endif
  }
}

// MARK: - Cross-Platform Background Color
struct AdaptiveBackgroundModifier: ViewModifier {
  func body(content: Content) -> some View {
#if os(macOS)
    content.background(Color(NSColor.windowBackgroundColor))
#else
    content.background(Color(UIColor.systemGroupedBackground))
#endif
  }
}

// MARK: - Convenience View Extensions
extension View {
  /// Applies a clean insetGrouped style on iOS and an inset style on macOS.
  func adaptiveListStyle() -> some View {
    self.modifier(AdaptiveListStyleModifier())
  }
  
  /// Applies systemGroupedBackground on iOS and windowBackgroundColor on macOS.
  func adaptiveBackground() -> some View {
    self.modifier(AdaptiveBackgroundModifier())
  }
}
