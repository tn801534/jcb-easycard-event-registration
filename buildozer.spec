[app]

# (str) Title of your application
title = JCB悠遊卡登錄

# (str) Package name
package.name = jcbeasycard

# (str) Package domain (needed for android/ios packaging)
package.domain = com.bless7103

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (pattern matching)
source.include_exts = py,png,jpg,kv,atlas,ini,txt,ttf

# (list) List of inclusions using pattern matching
source.include_patterns = *.py,*.ini,*.kv,requirements.txt

# (list) Source files to exclude (pattern matching)
source.exclude_dirs = tests, __pycache__, .git, .pytest_cache

# (list) List of directory to exclude from the APK
source.exclude_patterns = jcb.py, schedule_jcb.ps1

# (str) Application versioning
version = 1.0.0

# (str) Requirements pip packages
requirements = python3,kivy,requests_async,configobj,lxml,asyncio_read_write_lock

# (str) Presplash of the application
presplash.filename = %(source.dir)s/android/res/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/android/res/icon.png

# (str) Orientation (portrait, landscape or sensor)
orientation = portrait

# (list) Permissions
android.permissions = INTERNET

# (int) Android API level to use
android.api = 31

# (int) Minimum API required
android.minapi = 21

# (int) Android SDK version to use
android.sdk = 31

# (str) Android NDK version to use
android.ndk = 23b

# (bool) Enable AndroidX support
android.enable_androidx = True

# (str) Path to the Android app source code
android.add_src =

# (str) Python-for-android repo to use
p4a.source = git+https://github.com/kivy/python-for-android.git

# (str) Requirements of the application
# (list) Permissions

# (list) Android added JARs
android.add_jars =

# (bool) If True, then skip trying to update the SDK
android.avoid_old_so = True

# (str) The Android arch to build for
android.archs = arm64-v8a

# (str) Signing key name
# android.keyalias =

# (str) Signing key password
# android.keystore_password =

# (list) Android services
android.services =

# (bool) Use the default activity (useful for single-click)
android.use_default_activity = True

# (str) Branch of python-for-android
p4a.branch = develop

# (str) Local directory with python-for-android source (overrides p4a.branch)
# p4a.local_p4a_dir =

# (str) A filename for the debug APK
# android.debug_apk_name = jcb-debug.apk

# (str) A filename for the release APK
# android.release_apk_name = jcb-release.apk

[buildozer]

# (int) Log level (0=error, 1=info, 2=debug)
log_level = 1

# (path) Path to the build directory
warn_on_root = 0

# (str) Path to the build directory
# build_dir = ../.buildozer

# (str) Path to the Android platform directory
# android.platform_dir = ~/.buildozer/android/platform

[app:ios]
# (str) Title of your application
# title = JCB悠遊卡登錄

[app:android]
# (str) Supported architectures
# android.arch = arm64-v8a, armeabi-v7a
