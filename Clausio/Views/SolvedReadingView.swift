import SwiftUI
import AVFoundation

struct SolvedReadingView: View {
    @ObservedObject var vm: GameViewModel
    var onPlayAgain: () -> Void
    var onNextStory: () -> Void

    @State private var speechSynthesizer = AVSpeechSynthesizer()
    @State private var playingRowId: Int? = nil
    @State private var appeared = false

    private var sentences: [(rowId: Int, fullText: String, englishTranslation: String?, chunks: [(text: String, furigana: String)])] {
        (1...5).compactMap { rowId in
            let rowTiles = vm.tiles
                .filter { $0.originalRowId == rowId }
                .sorted { $0.originalColumnId < $1.originalColumnId }

            guard !rowTiles.isEmpty else { return nil }

            return (
                rowId: rowId,
                fullText: rowTiles.map(\.text).joined(),
                englishTranslation: vm.sentenceTranslationsById[rowId],
                chunks: rowTiles.map { (text: $0.text, furigana: $0.furigana) }
            )
        }
    }

    var body: some View {
        NavigationView {
            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: 28) {
                    victoryHeader
                        .padding(.top, 28)

                    readAllButton

                    sentenceCards
                        .padding(.horizontal, 16)

                    actionButtons
                        .padding(.bottom, 44)
                }
            }
            .navigationTitle("Story Review")
            .adaptiveNavigationBarTitleDisplayMode()
            .onAppear {
                withAnimation(.spring(response: 0.7, dampingFraction: 0.72)) {
                    appeared = true
                }
            }
            .onDisappear {
                speechSynthesizer.stopSpeaking(at: .immediate)
            }
        }
    }

    private var victoryHeader: some View {
        VStack(spacing: 10) {
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 56))
                .foregroundStyle(Color.accentColor)
                .scaleEffect(appeared ? 1.0 : 0.2)
                .opacity(appeared ? 1.0 : 0)

            Text("Story Complete!")
                .font(.title.bold())
                .opacity(appeared ? 1.0 : 0)
                .offset(y: appeared ? 0 : 10)

            Text("You rebuilt all 5 sentences.")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .opacity(appeared ? 1.0 : 0)
        }
        .animation(.spring(response: 0.6, dampingFraction: 0.7), value: appeared)
    }

    private var readAllButton: some View {
        Button(action: readAllSentences) {
            Label("Read All Aloud", systemImage: "speaker.wave.3.fill")
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(Capsule().fill(Color.accentColor))
                .foregroundColor(.white)
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 20)
        .opacity(appeared ? 1.0 : 0)
        .animation(.easeIn.delay(0.3), value: appeared)
    }

    private var sentenceCards: some View {
        VStack(spacing: 14) {
            ForEach(Array(sentences.enumerated()), id: \.element.rowId) { idx, sentence in
                SentenceCardView(
                    rowId: sentence.rowId,
                    fullText: sentence.fullText,
                    englishTranslation: sentence.englishTranslation,
                    chunks: sentence.chunks,
                    isPlaying: playingRowId == sentence.rowId,
                    accentColor: vm.colorForCategory(sentence.rowId)
                ) {
                    withAnimation { playingRowId = sentence.rowId }
                    speakSentence(sentence.fullText)
                }
                .opacity(appeared ? 1.0 : 0)
                .offset(y: appeared ? 0 : 20)
                .animation(
                    .spring(response: 0.5, dampingFraction: 0.8).delay(0.2 + Double(idx) * 0.09),
                    value: appeared
                )
            }
        }
    }

    private var actionButtons: some View {
        HStack(spacing: 14) {
            Button(action: {
                speechSynthesizer.stopSpeaking(at: .immediate)
                onPlayAgain()
            }) {
                Label("Play Again", systemImage: "arrow.clockwise")
                    .font(.subheadline.bold())
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .strokeBorder(Color.secondary.opacity(0.35), lineWidth: 1)
                    )
                    .foregroundColor(.primary)
            }
            .buttonStyle(.plain)

            Button(action: {
                speechSynthesizer.stopSpeaking(at: .immediate)
                onNextStory()
            }) {
                Label("Next Story", systemImage: "book.pages.fill")
                    .font(.subheadline.bold())
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(RoundedRectangle(cornerRadius: 12).fill(Color.accentColor))
                    .foregroundColor(.white)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 20)
        .opacity(appeared ? 1.0 : 0)
        .animation(.easeIn.delay(0.65), value: appeared)
    }

    private func speakSentence(_ text: String) {
        speechSynthesizer.stopSpeaking(at: .immediate)
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "ja-JP")
        utterance.rate = 0.42
        speechSynthesizer.speak(utterance)
    }

    private func readAllSentences() {
        speechSynthesizer.stopSpeaking(at: .immediate)
        withAnimation { playingRowId = nil }
        let joined = sentences.map(\.fullText).joined(separator: "。　")
        speakSentence(joined)
    }
}

struct SentenceCardView: View {
    let rowId: Int
    let fullText: String
    let englishTranslation: String?
    let chunks: [(text: String, furigana: String)]
    let isPlaying: Bool
    let accentColor: Color
    var onPlay: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Sentence \(rowId)")
                    .font(.caption.bold())
                    .foregroundColor(accentColor)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Capsule().fill(accentColor.opacity(0.12)))

                Spacer()

                Button(action: onPlay) {
                    Image(systemName: isPlaying ? "speaker.wave.2.fill" : "play.circle")
                        .font(.title3)
                        .foregroundColor(isPlaying ? accentColor : .secondary)
                }
                .buttonStyle(.plain)
            }

            Text(fullText)
                .font(.system(size: 17, weight: .medium))
                .foregroundColor(.primary)
                .lineSpacing(3)

            if let englishTranslation,
               !englishTranslation.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                Text(englishTranslation)
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Divider().padding(.vertical, 2)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(alignment: .top, spacing: 6) {
                    ForEach(Array(chunks.enumerated()), id: \.offset) { _, chunk in
                        VStack(spacing: 2) {
                            Text(chunk.furigana.isEmpty ? " " : chunk.furigana)
                                .font(.system(size: 9))
                                .foregroundColor(.secondary)
                                .lineLimit(1)

                            Text(chunk.text)
                                .font(.system(size: 13, weight: .medium))
                                .foregroundColor(.primary)
                        }
                        .padding(.horizontal, 5)
                        .padding(.vertical, 3)
                        .background(
                            RoundedRectangle(cornerRadius: 5)
                                .fill(accentColor.opacity(0.08))
                        )
                    }
                }
                .padding(.vertical, 2)
            }
        }
        .padding(14)
        .background(RoundedRectangle(cornerRadius: 14).fill(Color.secondary.opacity(0.07)))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .strokeBorder(isPlaying ? accentColor.opacity(0.5) : Color.clear, lineWidth: 1.5)
        )
        .animation(.easeInOut(duration: 0.25), value: isPlaying)
    }
}
