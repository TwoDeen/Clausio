//
//  StorySelectionView.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 12/06/2026.
//  Copyright ©️ 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI

struct StorySelectionView: View {
  // --- STATE MANAGEMENT ---
  @State private var stories: [Story] = []
  @State private var selectedLevel = "N4"
  @State private var isLoading = false
  @State private var errorMessage: String? = nil
  @State private var searchText = ""
  
  @State private var isNewsModeActive = false
  
  // --- ENVIRONMENT DEFINITIONS ---
  let levels = ["N5", "N4", "N3", "N2", "N1"]
  
  // 🚀 CHANGE 1: iOS device now hits Render; simulator/macOS stay on localhost
  var backendURL: String {
#if targetEnvironment(simulator)
    return "http://localhost:8000"          // Xcode simulator → local dev server
#elseif os(macOS)
    return "http://localhost:8000"          // macOS → local dev server
#else
    return "https://clausio-api.onrender.com"  // iOS device → Render free tier
#endif
  }
  
  var onPuzzleLoaded: (GamePayload) -> Void
  
  private var filteredStories: [Story] {
    if searchText.isEmpty {
      return stories
    } else {
      return stories.filter { story in
        let displayTitle = isNewsModeActive
        ? (story.name.components(separatedBy: "|").last ?? story.name)
        : story.name
        return displayTitle.localizedCaseInsensitiveContains(searchText)
      }
    }
  }
  
  var body: some View {
    NavigationView {
      VStack(spacing: 0) {
        
        Picker("Content Source", selection: $isNewsModeActive) {
          Text("Aozora Books").tag(false)
          // 🚀 CHANGE 2: Renamed — now routes N5/N4 → Easy, N3–N1 → Regular
          Text("NHK News").tag(true)
        }
        .pickerStyle(.palette)
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(Color.platformGroupedBackground)
        
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
        
        if isLoading {
          Spacer()
          VStack(spacing: 16) {
            ProgressView()
              .scaleEffect(1.5)
            Text(isNewsModeActive ? "Loading News Puzzle..." : "Parsing Japanese Text...")
              .font(.headline)
              .foregroundColor(.secondary)
            // 🚀 CHANGE 3: Removed GiNZA reference — Render serves precomputed files
            Text(isNewsModeActive ? "Fetching precomputed article matrix." : "GiNZa is compiling grammatical dependencies.")
              .font(.caption)
              .foregroundColor(.gray)
          }
          Spacer()
        } else if filteredStories.isEmpty && !searchText.isEmpty {
          ContentUnavailableView.search(text: searchText)
        } else if stories.isEmpty {
          ContentUnavailableView {
            Label(isNewsModeActive ? "No News Available" : "No Stories Available",
                  systemImage: "wifi.slash")
          } description: {
            Text("Could not connect to backend at \(backendURL). Please check network.")
          } actions: {
            Button("Retry Connection", action: fetchStoryList)
              .buttonStyle(.borderedProminent)
          }
        } else {
          List(filteredStories) { story in
            Button(action: {
              generateAndLoadPuzzle(for: story)
            }) {
              HStack(spacing: 16) {
                Image(systemName: isNewsModeActive ? "newspaper.fill" : "book.closed.fill")
                  .font(.title2)
                  .foregroundColor(.accentColor)
                  .frame(width: 40, height: 40)
                  .background(Color.accentColor.opacity(0.1))
                  .cornerRadius(8)
                
                VStack(alignment: .leading, spacing: 4) {
                  let displayTitle = isNewsModeActive
                  ? (story.name.components(separatedBy: "|").last ?? story.name)
                  : story.name
                  
                  Text(displayTitle)
                    .font(.headline)
                    .foregroundColor(.primary)
                  
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
      // 🚀 FIX: Both onChange modifiers anchored to the NavigationView content VStack
      //    (previously .onChange(of: selectedLevel) was a dangling modifier)
      .onChange(of: isNewsModeActive) { _ in
        fetchStoryList()
      }
      .onChange(of: selectedLevel) { _ in
        if isNewsModeActive { fetchStoryList() }
      }
      .navigationTitle(isNewsModeActive ? "NHK News" : "Clausio Stories")
#if os(iOS)
      .searchable(text: $searchText,
                  placement: .navigationBarDrawer(displayMode: .always),
                  prompt: "Search items by title...")
#else
      .searchable(text: $searchText, placement: .toolbar, prompt: "Search items by title...")
#endif
      .onAppear(perform: fetchStoryList)
    }
  }
  
  // --- SERVICE FUNCTIONS (API LAYER) ---
  
  func fetchStoryList() {
    let targetEndpoint: String
    if isNewsModeActive {
      targetEndpoint = "/api/news/topics?level=\(selectedLevel)"
    } else {
      targetEndpoint = "/api/stories"
    }
    guard let url = URL(string: "\(backendURL)\(targetEndpoint)") else { return }
    
    errorMessage = nil
    stories = []
    
    var request = URLRequest(url: url)
    request.cachePolicy = .reloadIgnoringLocalCacheData
    
    URLSession.shared.dataTask(with: request) { data, response, error in
      if let error = error {
        DispatchQueue.main.async {
          self.errorMessage = "Connection failed: \(error.localizedDescription)"
        }
        return
      }
      
      guard let data = data else { return }
      
      do {
        let listKey = isNewsModeActive ? "topics" : "stories"
        
        let jsonDict = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        guard let listArray = jsonDict?[listKey] as? [[String: Any]] else {
          throw NSError(domain: "", code: -1,
                        userInfo: [NSLocalizedDescriptionKey: "Invalid response structure"])
        }
        
        let parsedItems = listArray.compactMap { dict -> Story? in
          if isNewsModeActive {
            let newsId     = dict["id"]    as? String ?? UUID().uuidString
            let cleanTitle = dict["title"] as? String ?? "Untitled News"
            let packedName = "\(newsId)|\(cleanTitle)"
            let serverPath = dict["summary_html"] as? String ?? ""
            let safeUniquePath = "\(serverPath)|[\(UUID().uuidString)]"
            return Story(name: packedName, relative_path: safeUniquePath)
          } else {
            return Story(
              name:          dict["name"]          as? String ?? "Unknown File",
              relative_path: dict["relative_path"] as? String ?? ""
            )
          }
        }
        
        DispatchQueue.main.async {
          self.stories = parsedItems
        }
      } catch {
        DispatchQueue.main.async {
          self.errorMessage = "Failed parsing story list."
        }
      }
    }.resume()
  }
  
  func generateAndLoadPuzzle(for story: Story) {
    let targetEndpoint = isNewsModeActive
    ? "/api/news/puzzle/generate"
    : "/api/puzzle/generate"
    guard let url = URL(string: "\(backendURL)\(targetEndpoint)") else { return }
    
    withAnimation {
      isLoading    = true
      errorMessage = nil
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.cachePolicy = .reloadIgnoringLocalCacheData
    
    var bodyPayload: [String: String] = [:]
    
    if isNewsModeActive {
      let components  = story.name.components(separatedBy: "|")
      let extractedId = components.first ?? UUID().uuidString
      bodyPayload = [
        "news_id":      extractedId,
        "summary_html": story.relative_path,
        "level":        selectedLevel,
      ]
    } else {
      bodyPayload = [
        "file_path": story.relative_path,
        "level":     selectedLevel,
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
      
      if let httpResponse = response as? HTTPURLResponse,
         httpResponse.statusCode != 200 {
        DispatchQueue.main.async {
          self.errorMessage = "Server error (\(httpResponse.statusCode))."
        }
        return
      }
      
      do {
        let gamePayload = try JSONDecoder().decode(GamePayload.self, from: data)
        DispatchQueue.main.async {
          self.onPuzzleLoaded(gamePayload)
        }
      } catch let jsonError {
        print("JSON decode error: \(jsonError)")
        DispatchQueue.main.async {
          self.errorMessage = "Puzzle data failed to decode."
        }
      }
    }.resume()
  }
}
