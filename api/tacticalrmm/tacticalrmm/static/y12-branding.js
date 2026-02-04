/**
 * Y12.AI Branding Configuration
 * Intelligent Remote Monitoring and Management
 */

window.Y12_BRANDING = {
  // Application Name
  appName: "Y12.AI",
  appTagline: "Intelligent Remote Monitoring and Management",

  // Company Information
  company: {
    name: "Y12.AI Inc.",
    website: "https://y12.ai",
    supportEmail: "support@y12.ai",
    docsUrl: "https://docs.y12.ai",
  },

  // Theme Colors
  colors: {
    primary: "#1a237e",
    primaryLight: "#534bae",
    primaryDark: "#000051",
    secondary: "#7c4dff",
    secondaryLight: "#b47cff",
    secondaryDark: "#3f1dcb",
    accent: "#00bcd4",
    accentLight: "#62efff",
    accentDark: "#008ba3",
    success: "#00c853",
    warning: "#ffc107",
    error: "#ff5252",
    info: "#2196f3",
  },

  // Dark Theme Colors
  darkTheme: {
    bgPrimary: "#0d1117",
    bgSecondary: "#161b22",
    bgTertiary: "#21262d",
    bgCard: "#1c2128",
    textPrimary: "#f0f6fc",
    textSecondary: "#8b949e",
    textMuted: "#6e7681",
    border: "#30363d",
    borderLight: "#484f58",
  },

  // Light Theme Colors
  lightTheme: {
    bgPrimary: "#ffffff",
    bgSecondary: "#f6f8fa",
    bgTertiary: "#eaeef2",
    bgCard: "#ffffff",
    textPrimary: "#1a237e",
    textSecondary: "#57606a",
    textMuted: "#8b949e",
    border: "#d0d7de",
    borderLight: "#e1e4e8",
  },

  // Logo Configuration
  logo: {
    text: "Y12.AI",
    icon: "mdi-robot",
    showText: true,
    showIcon: true,
  },

  // Feature Flags
  features: {
    showWelcomeMessage: true,
    showAIBadge: true,
    enableGoogleAuth: true,
    enableSSO: true,
  },

  // Footer Configuration
  footer: {
    copyright: `© ${new Date().getFullYear()} Y12.AI Inc. All rights reserved.`,
    links: [
      { text: "Documentation", url: "https://docs.y12.ai" },
      { text: "Privacy Policy", url: "https://y12.ai/privacy" },
      { text: "Terms of Service", url: "https://y12.ai/terms" },
    ],
  },

  // Login Page Configuration
  login: {
    title: "Welcome to Y12.AI",
    subtitle: "Intelligent Remote Monitoring and Management",
    showGoogleLogin: true,
    showSSOLogin: true,
    backgroundGradient: "linear-gradient(135deg, #1a237e 0%, #7c4dff 100%)",
  },

  // Dashboard Configuration
  dashboard: {
    welcomeMessage: "Welcome to Y12.AI Dashboard",
    showQuickStats: true,
    showAIInsights: true,
  },
};

// Apply branding to document title
if (typeof document !== "undefined") {
  document.title = window.Y12_BRANDING.appName;
}

// Export for module systems
if (typeof module !== "undefined" && module.exports) {
  module.exports = window.Y12_BRANDING;
}
