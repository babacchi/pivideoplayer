import objc
from AppKit import NSApplication, NSApplicationPresentationHideDock, NSApplicationPresentationAutoHideMenuBar

def hide_menubar_and_dock():
    NSApp = NSApplication.sharedApplication()
    options = NSApplicationPresentationHideDock | NSApplicationPresentationAutoHideMenuBar
    NSApp.setPresentationOptions_(options)
