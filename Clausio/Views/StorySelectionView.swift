import SwiftUI

// MARK: - Data Models

struct StoriesAPIResponse: Codable {
  let stories: [StoryItem]
}

struct StoryItem: Codable, Identifiable {
  let name: String
  let relative_path: String? // Optional so it doesn't crash if missing
  var id: String { name }
}

struct NewsAPIResponse: Codable {
  let status: String?
  let topics: [NewsTopic]
}

struct NewsTopic: Codable, Identifiable {
  let id: String
  let title: String?         // Optional
  let link: String?          // Optional
  let summary_html: String?  // Optional
}

// MARK: - Main View

struct StorySelectionView: View {
  var onPuzzleLoaded: (GamePayload) -> Void
  
  @State private var stories: [StoryItem] = []
  @State private var newsTopics: [NewsTopic] = []
  
  @State private var selectedTab = 0 // 0 = Stories, 1 = News
  @State private var selectedLevel = "N3"
  @State private var isLoadingList = false
  @State private var isGeneratingPuzzle = false
  @State private var errorMessage: String?
  
  let baseURL = "https://clausio.onrender.com"
  
  init(onPuzzleLoaded: @escaping (GamePayload) -> Void) {
    self.onPuzzleLoaded = onPuzzleLoaded
  }
  
  var body: some View {
    NavigationView {
      VStack {
        Picker("Content Type", selection: $selectedTab) {
          Text("Aozora Stories").tag(0)
          Text("NHK News").tag(1)
        }
        .pickerStyle(SegmentedPickerStyle())
        .padding()
        .onChange(of: selectedTab) { _ in fetchData() }
        
        if selectedTab == 1 {
          Picker("JLPT Level", selection: $selectedLevel) {
            Text("N5").tag("N5")
            Text("N4").tag("N4")
            Text("N3").tag("N3")
            Text("N2").tag("N2")
            Text("N1").tag("N1")
          }
          .pickerStyle(SegmentedPickerStyle())
          .padding(.horizontal)
          .onChange(of: selectedLevel) { _ in fetchData() }
        }
        
        if isLoadingList {
          ProgressView("Loading topics...")
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if isGeneratingPuzzle {
          ProgressView("Generating Puzzle...")
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let errorMessage = errorMessage {
          Text(errorMessage)
            .foregroundColor(.red)
            .multilineTextAlignment(.center)
            .padding()
          Button("Try Again") { fetchData() }
            .padding(.top)
        } else {
          List {
            if selectedTab == 0 {
              ForEach(stories) { story in
                Button(action: {
                  generateStoryPuzzle(storyName: story.name)
                }) {
                  Text(story.name).font(.headline)
                }
                .foregroundColor(.primary)
              }
            } else {
              ForEach(newsTopics) { topic in
                Button(action: {
                  generateNewsPuzzle(newsID: topic.id)
                }) {
                  VStack(alignment: .leading, spacing: 6) {
                    // Use a default string if title is nil
                    Text(topic.title ?? "No Title").font(.headline)
                    Text("ID: \(topic.id.prefix(15))...")
                      .font(.caption)
                      .foregroundColor(.gray)
                  }
                  .padding(.vertical, 4)
                }
                .foregroundColor(.primary)
              }
            }
          }
        }
      }
      .navigationTitle(selectedTab == 0 ? "Stories" : "News")
      .onAppear { fetchData() }
    }
  }
  
  // MARK: - Networking (List Fetching)
  
  func fetchData() {
    isLoadingList = true
    errorMessage = nil
    if selectedTab == 0 { fetchStories() } else { fetchNews(level: selectedLevel) }
  }
  
  func fetchStories() {
    guard let url = URL(string: "\(baseURL)/api/stories") else { return }
    URLSession.shared.dataTask(with: url) { data, response, error in
      DispatchQueue.main.async {
        self.isLoadingList = false
        if let error = error { self.errorMessage = error.localizedDescription; return }
        guard let data = data else { self.errorMessage = "No data"; return }
        
        do {
          let decoded = try JSONDecoder().decode(StoriesAPIResponse.self, from: data)
          self.stories = decoded.stories
        } catch {
          self.errorMessage = "Failed parsing stories."
          print("Stories Decode Error: \(error)")
        }
      }
    }.resume()
  }
  
  func fetchNews(level: String) {
    guard let url = URL(string: "\(baseURL)/api/news/topics?level=\(level)") else { return }
    
    URLSession.shared.dataTask(with: url) { data, response, error in
      DispatchQueue.main.async {
        self.isLoadingList = false
        if let error = error { self.errorMessage = error.localizedDescription; return }
        guard let data = data else { self.errorMessage = "No data"; return }
        
        // DEBUG: Print the raw string to see what the API actually sent
        if let rawString = String(data: data, encoding: .utf8) {
          print("DEBUG: Raw JSON received: \(rawString)")
        }
        
        do {
          let decoded = try JSONDecoder().decode(NewsAPIResponse.self, from: data)
          self.newsTopics = decoded.topics
        } catch let error as DecodingError {
          // Pinpoint the exact field that failed
          switch error {
            case .keyNotFound(let key, _):
              self.errorMessage = "Missing key: \(key.stringValue)"
            case .typeMismatch(let type, _):
              self.errorMessage = "Type mismatch: \(type)"
            default:
              self.errorMessage = "Decoding failed"
          }
          print("News Decode Error: \(error)")
        } catch {
          self.errorMessage = "Unknown error"
        }
      }
    }.resume()
  }
  
  // MARK: - Networking (Puzzle Generation)
  
  func generateStoryPuzzle(storyName: String) {
    guard let url = URL(string: "\(baseURL)/api/puzzle/generate") else { return }
    isGeneratingPuzzle = true
    errorMessage = nil
    
    let body: [String: String] = ["file_path": storyName, "level": selectedLevel]
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try? JSONEncoder().encode(body)
    
    URLSession.shared.dataTask(with: request) { data, _, error in
      DispatchQueue.main.async {
        self.isGeneratingPuzzle = false
        if let error = error { self.errorMessage = error.localizedDescription; return }
        guard let data = data else { self.errorMessage = "No data"; return }
        do {
          let payload = try JSONDecoder().decode(GamePayload.self, from: data)
          self.onPuzzleLoaded(payload)
        } catch {
          self.errorMessage = "Failed to load story puzzle."
          print(error)
        }
      }
    }.resume()
  }
  
  func generateNewsPuzzle(newsID: String) {
    guard let url = URL(string: "\(baseURL)/api/news/puzzle/generate") else { return }
    isGeneratingPuzzle = true
    errorMessage = nil
    
    let body: [String: String] = [
      "news_id": newsID,
      "summary_html": "",
      "level": selectedLevel
    ]
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.httpBody = try? JSONEncoder().encode(body)
    
    URLSession.shared.dataTask(with: request) { data, _, error in
      DispatchQueue.main.async {
        self.isGeneratingPuzzle = false
        if let error = error { self.errorMessage = error.localizedDescription; return }
        guard let data = data else { self.errorMessage = "No data"; return }
        do {
          let payload = try JSONDecoder().decode(GamePayload.self, from: data)
          self.onPuzzleLoaded(payload)
        } catch {
          self.errorMessage = "Failed to load news puzzle."
          print(error)
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
