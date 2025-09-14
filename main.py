import sys
from PyQt6.QtWidgets import QApplication
from video_player import VideoPlayer
from streamdeck_handler import StreamDeckHandler

# アプリケーションのエントリーポイント
if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = VideoPlayer()
    streamdeck_handler = StreamDeckHandler()

    # Connect signals and slots
    streamdeck_handler.key_pressed.connect(controller.play_video_from_button)
    controller.video_loaded.connect(streamdeck_handler.update_key_with_filename)
    controller.playback_state_changed.connect(streamdeck_handler.update_key_playback_state)

    app.aboutToQuit.connect(streamdeck_handler.cleanup)
    controller.show()
    sys.exit(app.exec())