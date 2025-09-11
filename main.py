import sys
from PyQt6.QtWidgets import QApplication
from video_player import VideoPlayer

# アプリケーションのエントリーポイント
if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = VideoPlayer()
    controller.show()
    sys.exit(app.exec())