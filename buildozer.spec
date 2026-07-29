[app]

# (str) Title of your application
title = Security Monitor

# (str) Package name
package.name = secmonitor

# (str) Package domain (needs to be unique)
package.domain = com.yourorg.security

# (str) Source code where the main.py lives
source.dir = agent/

# (list) Source files to include (let almost everything through)
source.include_exts = py,png,jpg,kv,atlas,txt,json

# (list) Requirements — Python modules
requirements = python3,requests,phonenumbers,android,plyer

# (str) Application versioning
version = 1.0.0

# (int) Numeric version for Android
version.code = 1

# (str) Presplash of the application
presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientations
orientation = portrait

# (bool) Indicate if the application should be fullscreen
fullscreen = 0

#
# Android specific
#

# (list) Permissions
android.permissions = \
    CAMERA, \
    READ_CALL_LOG, \
    READ_SMS, \
    READ_PHONE_STATE, \
    INTERNET, \
    ACCESS_NETWORK_STATE, \
    FOREGROUND_SERVICE, \
    RECEIVE_BOOT_COMPLETED, \
    POST_NOTIFICATIONS, \
    WAKE_LOCK

# (int) Target Android API level
android.api = 34

# (int) Minimum API level
android.minapi = 26

# (int) Android SDK version to use
android.sdk = 34

# (str) Android NDK version to use
android.ndk = 27b

# (str) Android NDK directory (if empty, it will be automatically downloaded)
android.ndk_path =

# (str) Android SDK directory (if empty, it will be automatically downloaded)
android.sdk_path =

# (str) ANT directory (if empty, it will be automatically downloaded)
android.ant_path =

# (bool) If True, then skip trying to update the Android SDK
# This can be useful to avoid excess Internet downloads
android.accept_sdk_license = True

# (list) The Android arch to build for
android.archs = arm64-v8a

# (str) Path to a custom AndroidManifest.xml
android.manifest =

# (str) Presplash background color (for #ffffff)
android.presplash_color = #1a1a2e

# (str) Log level for the app
android.log_loglevel = 2

# (bool) Copy library instead of making a libs symlink
android.copy_libs = 1

# (list) The Android Java added jar file
android.add_src =

# (str) Python for android branch
android.p4a_branch = master

#
# iOS specific
#

# (str) iOS app version
ios.version = 1.0.0

# (str) iOS icon
ios.icon.filename = %(source.dir)s/data/icon.png

# (str) iOS copyright
ios.copyright =

#
# OSX specific
#

# (str) OSX icon
osx.icon.filename = %(source.dir)s/data/icon.png

#
# Windows specific
#

# (str) Windows icon
win.icon.filename = %(source.dir)s/data/icon.png

#
# Build configuration
#

# (str) Build output directory
build.dir = build/

# (str) Build output binary directory
bin.dir = bin/

# (str) Android archs to build for
android.arch = arm64-v8a

# (bool) If True, then the app will use the default keyboard
android.use_default_keyboard = True
