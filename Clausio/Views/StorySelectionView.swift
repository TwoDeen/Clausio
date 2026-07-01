import SwiftUI

// MARK: - API Models

struct CorpusSourcesResponse: Codable {
  let sources: [CorpusSource]
}

struct CorpusSource: Codable, Identifiable, Hashable {
  let id: String
  let requires_vpn: Bool
  let available: Bool
  let supports: [String]?
  
  var displayName: String {
    switch id {
      case "aozora": return "Aozora"
      case "nhk_easy": return "NHK Easy"
      case "nhk_general": return "NHK General"
      case "t15": return "T15"
      case "wjt_sentdil": return "WJT SentDil"
      default:
        return id.replacingOccurrences(of: "_", with: " ").capitalized
    }
  }
}

struct CorpusTopicsResponse: Codable {
  let status: String
  let topics: [CorpusTopic]
}

struct CorpusTopic: Codable, Identifiable, Hashable {
  let id: String
  let title: String
  let link: String?
  let detected_level: String?
  
  var subtitleText: String {
    if let level = detected_level, !level.isEmpty {
      return level
    }
    return id
  }
}

// MARK: - Main View

struct StorySelectionView: View {
  var onPuzzleLoaded: (GamePayload) -> Void
  
  @State private var sources: [CorpusSource] = []
  @State private var topics: [CorpusTopic] = []
  
  @State private var selectedSourceID: String = ""
  @State private var selectedLevel: String = "N3"
  
  @State private var isLoadingSources = false
  @State private var isLoadingTopics = false
  @State private var isGeneratingPuzzle = false
  @State private var errorMessage: String?
  
  let baseURL = "https://clausio.onrender.com"
  
  var body: some View {
    NavigationView {
      VStack(spacing: 12) {
        if isLoadingSources && sources.isEmpty {
          Spacer()
          ProgressView("Loading sources...")
          Spacer()
        } else {
          sourcePicker
          levelPicker
          contentArea
        }
      }
      .padding(.top, 8)
      .navigationTitle("Corpus")
      .onAppear {
        fetchSources()
      }
    }
  }
  
  private var sourcePicker: some View {
    VStack(alignment: .leading, spacing: 6) {
      Text("Source")
        .font(.caption)
        .foregroundColor(.secondary)
        .padding(.horizontal)
      
      Picker("Source", selection: $selectedSourceID) {
        ForEach(sources.filter { $0.available }) { source in
          Text(source.displayName).tag(source.id)
        }
      }
      .pickerStyle(MenuPickerStyle())
      .padding(.horizontal)
      .onChange(of: selectedSourceID) { _ in
        resetLevelIfUnsupported()
        fetchTopics()
      }
    }
  }
  
  private var levelPicker: some View {
    VStack(alignment: .leading, spacing: 6) {
      Text("JLPT Level")
        .font(.caption)
        .foregroundColor(.secondary)
        .padding(.horizontal)
      
      Picker("JLPT Level", selection: $selectedLevel) {
        ForEach(availableLevelsForSelectedSource(), id: \.self) { level in
          Text(level).tag(level)
        }
      }
      .pickerStyle(SegmentedPickerStyle())
      .padding(.horizontal)
      .onChange(of: selectedLevel) { _ in
        fetchTopics()
      }
    }
  }
  
  @ViewBuilder
  private var contentArea: some View {
    if isLoadingTopics {
      Spacer()
      ProgressView("Loading topics...")
      Spacer()
    } else if isGeneratingPuzzle {
      Spacer()
      ProgressView("Loading puzzle...")
      Spacer()
    } else if let errorMessage = errorMessage {
      Spacer()
      VStack(spacing: 12) {
        Text(errorMessage)
          .foregroundColor(.red)
          .multilineTextAlignment(.center)
          .padding(.horizontal)
        Spacer()
      }
    } else if topics.isEmpty {
      Spacer()
      Text("No precomputed topics found for this source and level.")
        .foregroundColor(.secondary)
        .multilineTextAlignment(.center)
        .padding(.horizontal)
      Spacer()
    } else {
      List(topics) { topic in
        Button {
          generateCorpusPuzzle(topic: topic)
        } label: {
          VStack(alignment: .leading, spacing: 6) {
            Text(topic.title)
              .font(.headline)
              .foregroundColor(.primary)
            
            Text(topic.subtitleText)
              .font(.caption)
              .foregroundColor(.secondary)
              .lineLimit(1)
          }
          .padding(.vertical, 4)
        }
      }
      .listStyle(.plain)
    }
  }
  
  // MARK: - Helpers
  
  private func availableLevelsForSelectedSource() -> [String] {
    guard let source = sources.first(where: { $0.id == selectedSourceID }) else {
      return ["N5", "N4", "N3", "N2", "N1"]
    }
    
    if let supports = source.supports, !supports.isEmpty {
      return supports
    }
    
    return ["N5", "N4", "N3", "N2", "N1"]
  }
  
  private func resetLevelIfUnsupported() {
    let levels = availableLevelsForSelectedSource()
    if !levels.contains(selectedLevel), let first = levels.first {
      selectedLevel = first
    }
  }
  
  // MARK: - Networking
  
  private func fetchSources() {
    guard let url = URL(string: "\(baseURL)/api/corpus/sources") else { return }
    
    isLoadingSources = true
    errorMessage = nil
    
    URLSession.shared.dataTask(with: url) { data, response, error in
      DispatchQueue.main.async {
        self.isLoadingSources = false
        
        if let error = error {
          self.errorMessage = error.localizedDescription
          return
        }
        
        guard let httpResponse = response as? HTTPURLResponse else {
          self.errorMessage = "Invalid server response."
          return
        }
        
        guard let data = data else {
          self.errorMessage = "No data from corpus sources API."
          return
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
          self.errorMessage = "Corpus sources API returned HTTP \(httpResponse.statusCode)."
          return
        }
        
        do {
          let decoded = try JSONDecoder().decode(CorpusSourcesResponse.self, from: data)
          self.sources = decoded.sources.filter { $0.available }
          
          if self.selectedSourceID.isEmpty, let first = self.sources.first {
            self.selectedSourceID = first.id
          }
          
          self.resetLevelIfUnsupported()
          self.fetchTopics()
        } catch {
          self.errorMessage = "Failed parsing corpus sources."
          print("Corpus Sources Decode Error: \(error)")
        }
      }
    }.resume()
  }
  
  private func fetchTopics() {
    guard !selectedSourceID.isEmpty else { return }
    
    guard let encodedSource = selectedSourceID.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
          let url = URL(string: "\(baseURL)/api/corpus/topics?source=\(encodedSource)&level=\(selectedLevel)") else {
      return
    }
    
    isLoadingTopics = true
    errorMessage = nil
    topics = []
    
    URLSession.shared.dataTask(with: url) { data, response, error in
      DispatchQueue.main.async {
        self.isLoadingTopics = false
        
        if let error = error {
          self.errorMessage = error.localizedDescription
          return
        }
        
        guard let httpResponse = response as? HTTPURLResponse else {
          self.errorMessage = "Invalid server response."
          return
        }
        
        guard let data = data else {
          self.errorMessage = "No data from corpus topics API."
          return
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
          self.errorMessage = "Corpus topics API returned HTTP \(httpResponse.statusCode)."
          return
        }
        
        do {
          let decoded = try JSONDecoder().decode(CorpusTopicsResponse.self, from: data)
          self.topics = decoded.topics
        } catch {
          self.errorMessage = "Failed parsing corpus topics."
          print("Corpus Topics Decode Error: \(error)")
        }
      }
    }.resume()
  }
  
  private func generateCorpusPuzzle(topic: CorpusTopic) {
    guard let url = URL(string: "\(baseURL)/api/corpus/puzzle/generate") else { return }
    
    isGeneratingPuzzle = true
    errorMessage = nil
    
    let body: [String: String] = [
      "source": selectedSourceID,
      "topic_id": topic.id,
      "level": selectedLevel
    ]
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try? JSONEncoder().encode(body)
    
    URLSession.shared.dataTask(with: request) { data, response, error in
      DispatchQueue.main.async {
        self.isGeneratingPuzzle = false
        
        if let error = error {
          self.errorMessage = error.localizedDescription
          return
        }
        
        guard let httpResponse = response as? HTTPURLResponse else {
          self.errorMessage = "Invalid server response."
          return
        }
        
        guard let data = data else {
          self.errorMessage = "No puzzle data returned."
          return
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
          self.errorMessage = "Corpus puzzle API returned HTTP \(httpResponse.statusCode)."
          return
        }
        
        do {
          let payload = try JSONDecoder().decode(GamePayload.self, from: data)
          self.onPuzzleLoaded(payload)
        } catch {
          self.errorMessage = "Failed to load precomputed puzzle."
          print("Corpus Puzzle Decode Error: \(error)")
        }
      }
    }.resume()
  }
}

struct StorySelectionView_Previews: PreviewProvider {
  static var previews: some View {
    StorySelectionView(onPuzzleLoaded: { _ in })
  }
}
