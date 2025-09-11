from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent


# 動画再生専用のウィンドウクラス
class PlayerWindow(QWidget):
    # コンストラクタ
    def __init__(self, controller):
        super().__init__()
        self.controller = controller  # メインコントローラーへの参照を保持
        self.setStyleSheet("background-color: black;")  # 背景色を黒に設定
        
        # ビデオ表示用のウィジェットを作成
        self.video_widget = QVideoWidget()
        
        # レイアウトを設定
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # ウィンドウのマージンをなくす
        layout.addWidget(self.video_widget)
        self.setLayout(layout)

        # カーソルを非表示にする
        self.setCursor(Qt.CursorShape.BlankCursor)

    # キーが押されたときのイベントハンドラ
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        # Escapeキーが押されたら、まずコントローラーを再表示する
        if key == Qt.Key.Key_Escape:
            if not self.controller.controller_visible:
                self.controller.toggle_controller_visibility(True)
            else:
                self.close()
            return

        # Cキーでコントローラーの表示/非表示を切り替え
        if key == Qt.Key.Key_C:
            self.controller.toggle_controller_visibility()
            return

        # 数字キーとビデオインデックスのマッピング
        key_map = {
            Qt.Key.Key_1: 0, Qt.Key.Key_2: 1, Qt.Key.Key_3: 2,
            Qt.Key.Key_4: 3, Qt.Key.Key_5: 4, Qt.Key.Key_6: 5,
            Qt.Key.Key_7: 6, Qt.Key.Key_8: 7, Qt.Key.Key_9: 8,
        }
        # 押されたキーがマッピングにあれば、対応するビデオを再生
        if key in key_map:
            self.controller.play_video_from_button(key_map[key])
        else:
            # それ以外のキーはデフォルトの処理に任せる
            super().keyPressEvent(event)
