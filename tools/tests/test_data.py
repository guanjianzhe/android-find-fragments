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

# Real-world Android 11 dumpsys sample with nested fragments
ANDROID11_REAL_SAMPLE = """
ACTIVITY MANAGER ACTIVITIES (dumpsys activity activities)
  Stack #0:
    Running activities (most recent first):
      TaskRecord{12345 #123 A=com.example.app U=0 StackId=0 sz=1}
        Run #0: ActivityRecord{67890 u0 com.example.app/.MainActivity t123}
          Intent { act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER] flg=0x10000000 cmp=com.example.app/.MainActivity }
          ProcessRecord{abcde 12345:com.example.app/u0a123}
    mResumedActivity: ActivityRecord{67890 u0 com.example.app/.MainActivity t123}
    mLastPausedActivity: ActivityRecord{67890 u0 com.example.app/.MainActivity t123}
""".strip()

# Real-world Android 15 dumpsys sample with multiple windows
ANDROID15_REAL_SAMPLE = """
ACTIVITY MANAGER ACTIVITIES (dumpsys activity activities)
Display #0 (activities from top to bottom):
  Task #123
    * TaskFragment{a1b2c3 mode=MULTI_WINDOW}
      * Activity{d4e5f6 u0 com.example.app/.ui.MainActivity} t123
        topResumedActivity=ActivityRecord{d4e5f6 u0 com.example.app/.ui.MainActivity t123}
        mResumedActivity: null
    mTopResumedActivity: ActivityRecord{d4e5f6 u0 com.example.app/.ui.MainActivity t123}
""".strip()

# Real-world fragment dump with system fragments and user fragments
REAL_FRAGMENTS_SAMPLE = """
Local FragmentActivity 2a60509 State:
  mCreated=true mResumed=true mStopped=false
  Active Fragments:
    #0: ReportFragment{9b18539 #0 androidx.lifecycle.LifecycleDispatcher.report_fragment_tag}
      mFragmentId=#0 mContainerId=#0 mTag=androidx.lifecycle.LifecycleDispatcher.report_fragment_tag
      mState=5 mIndex=0 mWho=android:fragment:0 mBackStackNesting=0
    #1: HomeFragment{7f51f50} (be44e86e-2570-4594-9f36-a06c322a4fbe id=0x7f020032)
      mFragmentId=#0x7f020032 mContainerId=#0x7f020030 mTag=home_fragment
      mState=7 mIndex=1 mWho=android:fragment:1 mBackStackNesting=0
    #2: ProfileFragment{8e62g61} (cf55f97f-3681-5605-af47-b17d433b5fcd id=0x7f020033)
      mFragmentId=#0x7f020033 mContainerId=#0x7f020030 mTag=profile_fragment
      mState=7 mIndex=2 mWho=android:fragment:2 mBackStackNesting=0
  Added Fragments:
    #0: ReportFragment{9b18539 #0 androidx.lifecycle.LifecycleDispatcher.report_fragment_tag}
    #1: HomeFragment{7f51f50} (be44e86e-2570-4594-9f36-a06c322a4fbe id=0x7f020032)
    #2: ProfileFragment{8e62g61} (cf55f97f-3681-5605-af47-b17d433b5fcd id=0x7f020033)
  Back Stack Index: 0
  FragmentManager misc state:
    mHost=androidx.fragment.app.FragmentActivity$HostCallbacks@a9f2781
    mContainer=androidx.fragment.app.FragmentActivity$HostCallbacks@a9f2781
    mCurState=7 mStateSaved=false mStopped=false mDestroyed=false
""".strip()
