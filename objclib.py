import objc
from AppKit import NSApplication, NSApplicationPresentationHideDock, NSApplicationPresentationHideMenuBar

def hide_menubar_and_dock():
    NSApp = NSApplication.sharedApplication()
    options = NSApplicationPresentationHideDock | NSApplicationPresentationHideMenuBar
    NSApp.setPresentationOptions_(options)
