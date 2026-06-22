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
  
  // 🚀 NEW STATE: Tracks which feed modality is currently active
  @State private var isNewsModeActive = false
  
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
        // Extract the clean title segment for searching if in news mode
        let displayTitle = isNewsModeActive ? (story.name.components(separatedBy: "|").last ?? story.name) : story.name
        return displayTitle.localizedCaseInsensitiveContains(searchText)
      }
    }
  }
  
  var body: some View {
    NavigationView {
      VStack(spacing: 0) {
        
        // 🚀 Content Source Toggle (Switch between Local Books and Live RSS Feed)
        Picker("Content Source", selection: $isNewsModeActive) {
          Text("Aozora Books").tag(false)
          Text("Live NHK Easy").tag(true)
        }
        .pickerStyle(.palette)
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(Color.platformGroupedBackground)
        .onChange(of: isNewsModeActive) { _ in
          fetchStoryList() // Auto-refresh rows when user flips mode
        }
        
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
            Text(isNewsModeActive ? "Structuring News Matrix..." : "Parsing Japanese Text...")
              .font(.headline)
              .foregroundColor(.secondary)
            Text(isNewsModeActive ? "Isolating sequential news sentences." : "GiNZa is compiling grammatical dependencies.")
              .font(.caption)
              .foregroundColor(.gray)
          }
          Spacer()
        } else if filteredStories.isEmpty && !searchText.isEmpty {
          // Visual feedback specifically for when search yields 0 filter results
          ContentUnavailableView.search(text: searchText)
        } else if stories.isEmpty {
          ContentUnavailableView {
            Label(isNewsModeActive ? "No News Available" : "No Stories Available", systemImage: "wifi.slash")
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
                // 🚀 DYNAMIC ICON: Swap book icon for a news panel card graphic when reading RSS
                Image(systemName: isNewsModeActive ? "newspaper.fill" : "book.closed.fill")
                  .font(.title2)
                  .foregroundColor(.accentColor)
                  .frame(width: 40, height: 40)
                  .background(Color.accentColor.opacity(0.1))
                  .cornerRadius(8)
                
                VStack(alignment: .leading, spacing: 4) {
                  // 🚀 STRIP ID OUT OF RENDER LAYER: Show only the clean headline string
                  let displayTitle = isNewsModeActive ? (story.name.components(separatedBy: "|").last ?? story.name) : story.name
                  
                  Text(displayTitle)
                    .font(.headline)
                    .foregroundColor(.primary)
                  
                  // Hide internal server path tokens when viewing dynamic news
                  if !isNewsModeActive {
                    Text(story.relative_path)
                      .font(.caption2)
                      .lineLimit(1)
                      .foregroundColor(.secondary)
                  }
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
      .navigationTitle(isNewsModeActive ? "NHK Easy News" : "Clausio Stories")
      // 🔍 Appends the native platform search bar interaction layer right under the title block
#if os(iOS)
      .searchable(text: $searchText, placement: .navigationBarDrawer(displayMode: .always), prompt: "Search items by title...")
#else
      .searchable(text: $searchText, placement: .toolbar, prompt: "Search items by title...")
#endif
      .onAppear(perform: fetchStoryList)
    }
  }
  
  // --- SERVICE FUNCTIONS (API LAYER) ---
  func fetchStoryList() {
    // 🚀 TARGET ROUTE MODIFIER: Select correct API channel based on source toggle
    let targetEndpoint = isNewsModeActive ? "/api/news/topics" : "/api/stories"
    guard let url = URL(string: "\(backendURL)\(targetEndpoint)") else { return }
    errorMessage = nil
    stories = [] // Instantly clear grid list to visually indicate transition reload
    
    URLSession.shared.dataTask(with: url) { data, response, error in
      if let error = error {
        DispatchQueue.main.async {
          self.errorMessage = "Connection failed: \(error.localizedDescription)"
        }
        return
      }
      
      guard let data = data else { return }
      
      do {
        // News topics array maps key to "topics", classic books map to "stories"
        let listKey = isNewsModeActive ? "topics" : "stories"
        
        let jsonDict = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        guard let listArray = jsonDict?[listKey] as? [[String: Any]] else {
          throw NSError(domain: "", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid dictionary array target structure"])
        }
        
        // Re-map keys smoothly into your existing Story memberwise structure layout
        let parsedItems = listArray.compactMap { dict -> Story? in
          if isNewsModeActive {
            let newsId = dict["id"] as? String ?? UUID().uuidString
            let cleanTitle = dict["title"] as? String ?? "Untitled News"
            
            // 🚀 DELIMITER INJECTION: Pack unique id safely into the struct initializer
            let packedName = "\(newsId)|\(cleanTitle)"
            
            return Story(
              name: packedName,
              relative_path: dict["summary_html"] as? String ?? ""
            )
          } else {
            return Story(
              name: dict["name"] as? String ?? "Unknown File",
              relative_path: dict["relative_path"] as? String ?? ""
            )
          }
        }
        
        DispatchQueue.main.async {
          self.stories = parsedItems
        }
      } catch {
        DispatchQueue.main.async {
          self.errorMessage = "Failed parsing available story manifest files."
        }
      }
    }.resume()
  }
  
  func generateAndLoadPuzzle(for story: Story) {
    // 🚀 TARGET ROUTE MODIFIER: Forward requests to the live compilation block when necessary
    let targetEndpoint = isNewsModeActive ? "/api/news/puzzle/generate" : "/api/puzzle/generate"
    guard let url = URL(string: "\(backendURL)\(targetEndpoint)") else { return }
    
    withAnimation {
      isLoading = true
      errorMessage = nil
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    var bodyPayload: [String: String] = [:]
    
    if isNewsModeActive {
      // 🚀 DELIMITER UNPACKING: Slice string components back into separate logical elements
      let components = story.name.components(separatedBy: "|")
      let extractedId = components.first ?? UUID().uuidString
      
      bodyPayload = [
        "news_id": extractedId,
        "summary_html": story.relative_path, // Passes down the 5-sentence paragraph string context
        "level": selectedLevel
      ]
    } else {
      bodyPayload = [
        "file_path": story.relative_path,
        "level": selectedLevel
      ]
    }
    
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
