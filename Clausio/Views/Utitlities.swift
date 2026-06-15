//
//  Utitlities.swift
//  Clausio
//
//  Created by Mohideen Noordeen on 15/06/2026.
//  Copyright © 2026 Inforill Technologies Private Limited. All rights reserved.
//

import SwiftUI

// MARK: - Cross-Platform Color Extension Fallback
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
  
  /// Applies .inline navigation title display mode on iOS; no-op on macOS where the modifier is unavailable.
  func adaptiveNavigationBarTitleDisplayMode() -> some View {
#if os(iOS)
    self.navigationBarTitleDisplayMode(.inline)
#else
    self
#endif
  }
  
  /// Full-screen cover on iOS; falls back to a sheet on macOS where fullScreenCover is unavailable.
  func adaptiveFullScreenCover<Content: View>(
    isPresented: Binding<Bool>,
    onDismiss: (() -> Void)? = nil,
    @ViewBuilder content: @escaping () -> Content
  ) -> some View {
#if os(iOS)
    self.fullScreenCover(isPresented: isPresented, onDismiss: onDismiss, content: content)
#else
    self.sheet(isPresented: isPresented, onDismiss: onDismiss, content: content)
#endif
  }
}
