"""Constants and configuration for the ACF tool."""

# Fragment parsing anchors
FRAGMENT_ANCHORS = ("Added Fragments:", "Active Fragments:")

# Fragment parsing stoppers
FRAGMENT_STOPPERS = (
    "Removed Fragments:",
    "AutofillManager:",
    "Back Stack:",
    "Loaders:",
    "FragmentManager state:",
    "Host callbacks:",
    "FragmentManager:",
    "View Hierarchy:",
    "Window #",
)

# System fragments to filter out
SYSTEM_FRAGMENTS = {
    "ReportFragment",
    "SupportRequestManagerFragment", 
    "AutofillManager",
    "DialogFragment",
    "ListFragment",
    "PreferenceFragment",
    "WebViewFragment",
    "Fragment",
    "androidx.fragment.app.Fragment",
    "android.app.Fragment"
}

# Activity parsing keys
ACTIVITY_KEYS = ["topResumedActivity", "mResumedActivity"]

# Default timeout for ADB commands
DEFAULT_TIMEOUT = 10

# Build directories to skip when searching for source files
SKIP_DIRECTORIES = {
    ".git", ".gradle", "build", "out", "node_modules", 
    "venv", "__pycache__", ".idea", "target"
}
