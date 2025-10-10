"""Test data for ACF tool tests."""

# Android 11 sample
ANDROID11_SAMPLE = """
  mResumedActivity: ActivityRecord{2baae81 u0 com.example.app/.ui.MainActivity t2431 d0}
""".strip()

# Android 14 sample
ANDROID14_SAMPLE = """
  topResumedActivity=ActivityRecord{77b3dc7 u0 com.example.app/.ui.MainActivity t90}
""".strip()

# Fragment samples
FRAGMENTS_SAMPLE = """
Added Fragments:
  #0 com.example.app.ui.HomeFragment{123456}
  #1 com.example.app.ui.child.ChildFragment{abcdef}
  #2 com.example.app.ui.dialog.InfoDialogFragment{789abc}
AutofillManager:
""".strip()

FRAGMENTS_ACTIVE_SAMPLE = """
Active Fragments:
  #0: com.example.app.ui.TabFragment{000000}
  #1: NestedChildFragment{111111}
  #2: com.example.app.ui.list.ListFragment{222222}
Back Stack:
""".strip()

FRAGMENTS_COMPLEX_SAMPLE = """
Added Fragments:
  #0 com.example.app.ui.HomeFragment{123456}
  #1: com.example.app.ui.child.ChildFragment{abcdef}
  #2 com.example.app.ui.dialog.InfoDialogFragment{789abc}
  #3: NestedChildFragment{111111}
  #4 com.example.app.ui.tab.TabFragment{000000}
  ReportFragment{system}
  SupportRequestManagerFragment{system}
  AutofillManager:
""".strip()

FRAGMENTS_ANDROID_SYSTEM_SAMPLE = """
Added Fragments:
  #0 com.example.app.ui.HomeFragment{123456}
  #1: com.example.app.ui.child.ChildFragment{abcdef}
  DialogFragment{system}
  ListFragment{system}
  PreferenceFragment{system}
  WebViewFragment{system}
  Fragment{system}
  androidx.fragment.app.Fragment{system}
  android.app.Fragment{system}
  AutofillManager:
""".strip()

FULL_DUMPSYS_SAMPLE = """
ACTIVITY MANAGER ACTIVITIES (dumpsys activity activities)
Stack #0:
  Task #123:
    Activity #1: com.other.app/.OtherActivity
      Added Fragments:
        #0 com.other.app.ui.OtherFragment{111111}
      AutofillManager:
    Activity #2: com.example.app/.ui.MainActivity
      Added Fragments:
        #0 com.example.app.ui.HomeFragment{123456}
        #1 com.example.app.ui.ProfileFragment{789abc}
      AutofillManager:
    Activity #3: com.another.app/.AnotherActivity
      Added Fragments:
        #0 com.another.app.ui.AnotherFragment{222222}
      AutofillManager:
""".strip()

# Package-specific dumpsys sample (like external plugin uses)
PACKAGE_DUMPSYS_SAMPLE = """
ACTIVITY MANAGER ACTIVITIES (dumpsys activity com.example.app)
Stack #0:
  Task #123:
    Activity #2: com.example.app/.ui.MainActivity
      Local Activity 2a60509 State:
        mResumed=true mStopped=false mFinished=false
        Added Fragments:
          #0: HomeFragment{123456} (uuid tag=home)
          #1: ProfileFragment{789abc} (uuid tag=profile)
        FragmentManager misc state:
          mHost=androidx.fragment.app.FragmentActivity$HostCallbacks@46e81a1
          mContainer=androidx.fragment.app.FragmentActivity$HostCallbacks@46e81a1
          mCurState=7 mStateSaved=false mStopped=false mDestroyed=false
""".strip()
