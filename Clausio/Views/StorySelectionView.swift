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
  @State private var searchText = "" // 🔍 Tracks user's search query input
  
  // --- ENVIRONMENT DEFINITIONS ---
  let levels = ["N5", "N4", "N3", "N2", "N1"]
  
  var backendURL: String {
#if targetEnvironment(simulator)
    return "http://localhost:8000"
#else
    return "http://192.168.1.126:8000" // Local Network IP
#endif
  }
  
  var onPuzzleLoaded: (GamePayload) -> Void
  
  // 🧠 Computed property filters database query responses instantly based on matching names
  private var filteredStories: [Story] {
    if searchText.isEmpty {
      return stories
    } else {
      return stories.filter { story in
        story.name.localizedCaseInsensitiveContains(searchText)
      }
    }
  }
  
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
        
        // Content Switcher
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
        } else if filteredStories.isEmpty && !searchText.isEmpty {
          // Visual feedback specifically for when search yields 0 filter results
          ContentUnavailableView.search(text: searchText)
        } else if stories.isEmpty {
          ContentUnavailableView {
            Label("No Stories Available", systemImage: "wifi.slash")
          } description: {
            Text("Could not resolve backend catalog cluster at \(backendURL). Please check network configurations.")
          } actions: {
            Button("Retry Connection", action: fetchStoryList)
              .buttonStyle(.borderedProminent)
          }
        } else {
          // Render dynamically from the reactive computed filter pipeline
          List(filteredStories) { story in
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
      // 🔍 Appends the native platform search bar interaction layer right under the title block
#if os(iOS)
      .searchable(text: $searchText, placement: .navigationBarDrawer(displayMode: .always), prompt: "Search stories by title...")
#else
      .searchable(text: $searchText, placement: .toolbar, prompt: "Search stories by title...")
#endif
      .onAppear(perform: fetchStoryList)
    }
  }
  
  // --- SERVICE FUNCTIONS (API LAYER) ---
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
  
  func generateAndLoadPuzzle(for story: Story) {
    guard let url = URL(string: "\(backendURL)/api/puzzle/generate") else { return }
    
    withAnimation {
      isLoading = true
      errorMessage = nil
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
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
      
      if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode != 200 {
        DispatchQueue.main.async {
          self.errorMessage = "Server generation error (\(httpResponse.statusCode))."
        }
        return
      }
      
      do {
        let gamePayload = try JSONDecoder().decode(GamePayload.self, from: data)
        DispatchQueue.main.async {
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
