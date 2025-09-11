import sys
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QGridLayout, QWidget, \
                             QFileDialog, QHBoxLayout, QVBoxLayout, QSlider, QStyle, \
                             QComboBox, QLabel, QMenuBar, QMenu, QSizePolicy, QCheckBox)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QKeyEvent, QCloseEvent
from player_window import PlayerWindow
from objclib import hide_menubar_and_dock

# メインのビデオプレーヤーコントローラークラス
class VideoPlayer(QMainWindow):
    # コンストラクタ
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Player Controller")  # ウィンドウのタイトルを設定
        self.setGeometry(100, 100, 1000, 500)  # ウィンドウの位置とサイズを設定
        # 中央のウィジェットとメインレイアウトを設定
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # 再生コントロール用のレイアウト
        self.controls_layout = QHBoxLayout()
        self.main_layout.addLayout(self.controls_layout)

        # 再生/一時停止ボタン
        self.play_pause_button = QPushButton()
        self.play_pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.controls_layout.addWidget(self.play_pause_button)

        # 停止ボタン
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_video)
        self.controls_layout.addWidget(self.stop_button)

        # シークバー（再生位置のスライダー）
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.sliderMoved.connect(self.set_position)
        self.seek_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred) # シークバーを拡張
        self.controls_layout.addWidget(self.seek_slider)

        # 時間表示ラベル
        self.time_label = QLabel("--:--:-- / --:--:--")
        self.time_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        self.time_label.setFixedWidth(400) # 固定幅を設定
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter) # 右揃えと垂直中央揃え
        self.controls_layout.addWidget(self.time_label)

        # ビデオ選択ボタン用のグリッドレイアウト
        self.grid_layout = QGridLayout()
        self.main_layout.addLayout(self.grid_layout)

        # --- 設定用のUI要素 ---
        settings_layout = QHBoxLayout()

        # 出力モニター選択
        screen_selector_layout = QHBoxLayout()
        screen_selector_layout.addWidget(QLabel("出力モニタ:"))
        self.screens = QApplication.screens()
        self.screen_selector = QComboBox()
        self.screen_selector.addItems([screen.name() or f"Screen {i + 1}" for i, screen in enumerate(self.screens)])
        self.screen_selector.currentIndexChanged.connect(self.switch_screen)
        screen_selector_layout.addWidget(self.screen_selector)
        settings_layout.addLayout(screen_selector_layout)

        # 音声出力先選択
        audio_selector_layout = QHBoxLayout()
        audio_selector_layout.addWidget(QLabel("音声出力先:"))
        self.audio_devices = QMediaDevices.audioOutputs()
        self.audio_selector = QComboBox()
        self.audio_selector.addItems([device.description() for device in self.audio_devices])
        self.audio_selector.currentIndexChanged.connect(self.switch_audio_device)
        audio_selector_layout.addWidget(self.audio_selector)
        settings_layout.addLayout(audio_selector_layout)
        
        self.main_layout.addLayout(settings_layout)
        # --- 設定用のUI要素ここまで ---

        # 変数の初期化
        self.video_paths = {}  # ビデオファイルのパスを格納する辞書
        self.play_buttons = []  # 再生ボタンの参照を格納するリスト
        self.loop_checkboxes = []  # ループチェックボックスの参照を格納するリスト
        self.current_playing_button_index = -1  # 現在再生中のビデオのインデックス
        self.create_buttons()  # ボタンを生成

        # 現在再生中のファイル名表示ラベル
        self.current_playing_file_name = "停止中"
        self.current_video_label = QLabel(self.current_playing_file_name)
        self.main_layout.addWidget(self.current_video_label)

        # メディアプレーヤー関連のオブジェクトを初期化
        self.player_window = None  # 再生ウィンドウのインスタンス
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.switch_audio_device(self.audio_selector.currentIndex())  # デフォルトの音声出力先を設定

        # メディアプレーヤーのシグナルをスロットに接続
        self.media_player.errorOccurred.connect(self.media_player_error)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.playbackStateChanged.connect(self.update_play_pause_icon)
        
        # デフォルトのフォントサイズと最前面表示を設定
        self.set_font_size("medium")
        self.font_size = "medium"
        self.controller_visible = True
        
        # コントローラーを常に最前面に表示
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        # メニューバーを作成
        self.create_menu()
        self._create_player_window(QApplication.primaryScreen())
        # アプリ起動時にコントローラーの表示状態をメニューバーに反映 
        self.toggle_controller_visibility(self.controller_visible)
        
    # メニューバーを作成するメソッド
    def create_menu(self):
        menubar = self.menuBar()

        # 「ファイル」メニュー
        file_menu = menubar.addMenu("ファイル")
        export_action = file_menu.addAction("設定をエクスポート")
        export_action.triggered.connect(self.export_settings)
        import_action = file_menu.addAction("設定をインポート")
        import_action.triggered.connect(self.import_settings)

        # 「表示」メニュー（フォントサイズ変更）
        view_menu = menubar.addMenu("表示")
        small_font_action = view_menu.addAction("小")
        small_font_action.triggered.connect(lambda: self.set_font_size("small"))
        medium_font_action = view_menu.addAction("中")
        medium_font_action.triggered.connect(lambda: self.set_font_size("medium"))
        large_font_action = view_menu.addAction("大")
        large_font_action.triggered.connect(lambda: self.set_font_size("large"))

        view_menu.addSeparator()
        self.hide_controller_action = view_menu.addAction("コントローラーを隠す")
        self.hide_controller_action.triggered.connect(lambda: self.toggle_controller_visibility())
    
    # 設定をJSONファイルにエクスポートするメソッド
    def export_settings(self):
        # video_pathsのキーが数値だとJSONで問題になる可能性があるため文字列に変換
        video_paths_str_keys = {str(k): v for k, v in self.video_paths.items()}

        settings = {
            'video_paths': video_paths_str_keys,
            'screen_index': self.screen_selector.currentIndex(),
            'audio_index': self.audio_selector.currentIndex(),
            'font_size': self.font_size,
            'controller_visible': self.controller_visible,
        }

        # ファイル保存ダイアログを開く
        save_path, _ = QFileDialog.getSaveFileName(self, "設定をエクスポート", "", "JSON Files (*.json)")
        if save_path:
            if not save_path.endswith('.json'):
                save_path += '.json'
            with open(save_path, 'w') as f:
                json.dump(settings, f, indent=4)

    # 設定をJSONファイルからインポートするメソッド
    def import_settings(self):
        # ファイル選択ダイアログを開く
        load_path, _ = QFileDialog.getOpenFileName(self, "設定をインポート", "", "JSON Files (*.json)")
        if load_path:
            with open(load_path, 'r') as f:
                settings = json.load(f)

            video_paths_str_keys = settings.get('video_paths', {})
            # JSONのキー（文字列）を整数に変換してvideo_pathsを再構築
            self.video_paths = {int(k): v for k, v in video_paths_str_keys.items()}

            # スクリーンインデックスの検証と適用
            screen_index = settings.get('screen_index', 0)
            if screen_index >= self.screen_selector.count():
                screen_index = 0 # 範囲外ならデフォルトにリセット
            self.screen_selector.setCurrentIndex(screen_index)

            # オーディオインデックスの検証と適用
            audio_index = settings.get('audio_index', 0)
            if audio_index >= self.audio_selector.count():
                audio_index = 0 # 範囲外ならデフォルトにリセット
            self.audio_selector.setCurrentIndex(audio_index)

            # フォントサイズの適用
            self.set_font_size(settings.get('font_size', 'medium'))

            # コントローラーの表示状態を復元
            self.controller_visible = settings.get('controller_visible', True)
            self.showPlayerWindow()

            # UIを読み込んだ設定に合わせて更新
            self.update_ui_from_settings()

    # 読み込んだ設定に基づいてUI（ボタンの表示など）を更新するメソッド
    def update_ui_from_settings(self):
        for i in range(9):
            video_info = self.video_paths.get(i)
            if video_info and video_info.get('path'):
                file_path = video_info['path']
                filename = file_path.split('/')[-1]
                button = self.play_buttons[i]
                button.setToolTip(filename) # ボタンにマウスオーバーでフルパス表示
                # ファイル名が長すぎる場合は省略
                max_len = 25
                if len(filename) > max_len:
                    display_name = filename[:max_len-3] + "..."
                else:
                    display_name = filename
                button.setText(display_name)
                button.setEnabled(True)
                self.loop_checkboxes[i].setChecked(video_info.get('loop', False))
            else:
                # 読み込まれていないスロットのUIをリセット
                button = self.play_buttons[i]
                button.setText(f"Load Video {i + 1}")
                button.setToolTip("")
                button.setEnabled(False)
                self.loop_checkboxes[i].setChecked(False)

    def showPlayerWindow(self):
        self.setVisible(self.controller_visible)
        if self.controller_visible:
            self.raise_()
            self.activateWindow()

    def toggle_controller_visibility(self, visible=None):
        if visible is None:
            self.controller_visible = not self.controller_visible
        else:
            self.controller_visible = visible
        
        if self.controller_visible:
            self.hide_controller_action.setText("コントローラーを隠す(C)")
        else:
            self.hide_controller_action.setText("コントローラーを表示(C)")
        self.showPlayerWindow()

    # アプリケーション全体のフォントサイズを設定するメソッド
    def set_font_size(self, size):
        self.font_size = size
        if size == "small":
            font_size = 10
        elif size == "medium":
            font_size = 12
        elif size == "large":
            font_size = 14
        else:
            font_size = 12 # デフォルトは中サイズ
        
        # スタイルシートを使ってフォントサイズを適用
        QApplication.instance().setStyleSheet(f"* {{ font-size: {font_size}pt; }}")

    # 9つのビデオコントロールボタン群を作成するメソッド
    def create_buttons(self):
        for i in range(9):
            row = i // 3
            base_col = (i % 3) * 3  # 各スロットに3列（再生、読込、ループ）使う

            # 再生ボタン
            play_button = QPushButton(f"Load Video {i + 1}")
            play_button.clicked.connect(lambda checked, idx=i: self.play_video_from_button(idx))
            play_button.setEnabled(False) # 最初は無効
            self.grid_layout.addWidget(play_button, row, base_col)
            self.play_buttons.append(play_button)

            # 読込ボタン ("...")
            load_button = QPushButton("...")
            load_button.setFixedWidth(30)
            load_button.clicked.connect(lambda checked, b=play_button, idx=i: self.load_video(b, idx))
            self.grid_layout.addWidget(load_button, row, base_col + 1)

            # ループ再生チェックボックス
            loop_checkbox = QCheckBox("ループ")
            loop_checkbox.toggled.connect(lambda checked, idx=i: self.toggle_video_loop_setting(idx, checked))
            self.grid_layout.addWidget(loop_checkbox, row, base_col + 2)
            self.loop_checkboxes.append(loop_checkbox)

            # ビデオパス辞書を初期化
            self.video_paths[i] = {'path': None, 'loop': False}

    # ウィンドウが閉じられるときのイベント
    def closeEvent(self, event: QCloseEvent):
        # プレイヤーウィンドウが開いていればそれも閉じる
        if self.player_window and self.player_window.isVisible():
            self.player_window.close()
        event.accept()

    # キーが押されたときのイベントハンドラ（メインウィンドウ用）
    def keyPressEvent(self, event: QKeyEvent):
        # 数字キーとビデオインデックスのマッピング
        key_map = {
            Qt.Key.Key_1: 0, Qt.Key.Key_2: 1, Qt.Key.Key_3: 2,
            Qt.Key.Key_4: 3, Qt.Key.Key_5: 4, Qt.Key.Key_6: 5,
            Qt.Key.Key_7: 6, Qt.Key.Key_8: 7, Qt.Key.Key_9: 8,
        }
        key = event.key()
        # 押されたキーがマッピングにあれば、対応するビデオを再生
        if key in key_map:
            self.play_video_from_button(key_map[key])
        # Cキーでコントローラーの表示/非表示を切り替え
        elif key == Qt.Key.Key_C:
            self.toggle_controller_visibility()
            return
        else:
            # それ以外のキーはデフォルトの処理に任せる
            super().keyPressEvent(event)

    # プレイヤーウィンドウを作成して表示する内部メソッド
    def _create_player_window(self, screen):
        self.player_window = PlayerWindow(self)
        self.player_window.destroyed.connect(self.player_window_closed)
        self.media_player.setVideoOutput(self.player_window.video_widget)

        # 黒背景
        self.player_window.setStyleSheet("background-color: black;")
        
        # 擬似フルスクリーン（Spacesに移動しない）
        self.player_window.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.player_window.setGeometry(screen.geometry())
        self.player_window.show()
        self.player_window.raise_()

        if sys.platform == 'darwin':
            # macOS の Dock とメニューバーを隠す
            try:
                hide_menubar_and_dock()
            except Exception as e:
                print("Failed to hide menu bar:", e)
        elif sys.platform == 'win32':
            # Windows ではフルスクリーンモードにする
            self.player_window.showFullScreen()
        

    # 出力スクリーンを切り替えるメソッド
    def switch_screen(self):
        screen_index = self.screen_selector.currentIndex()
        screen = self.screens[screen_index] if 0 <= screen_index < len(self.screens) else QApplication.primaryScreen()
        self.player_window.setGeometry(screen.geometry())
        self.player_window.show()
        self.player_window.raise_()
        self.player_window.activateWindow()
        self.showPlayerWindow()

    # 音声出力デバイスを切り替えるメソッド
    def switch_audio_device(self, index):
        if 0 <= index < len(self.audio_devices):
            self.audio_output.setDevice(self.audio_devices[index])

    # ビデオファイルを読み込むメソッド
    def load_video(self, button, index):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Video", "", "Video Files (*.mp4 *.avi *.mkv)")
        if file_path:
            self.video_paths[index]['path'] = file_path
            filename = file_path.split('/')[-1]
            button.setToolTip(filename)
            # ファイル名が長すぎる場合は省略
            max_len = 25
            if len(filename) > max_len:
                display_name = filename[:max_len-3] + "..."
            else:
                display_name = filename
            button.setText(display_name)
            button.setEnabled(True)
            # プレイヤーウィンドウがなければ表示、あればスクリーンを切り替え
            if self.player_window is None:
                self.show_player_window()
            else:
                self.switch_screen()

    # ボタンからビデオを再生するメソッド
    def play_video_from_button(self, index):
        file_path = self.video_paths.get(index, {}).get('path')
        if file_path:
            # 前に再生していたボタンの色をリセット
            if self.current_playing_button_index != -1 and self.current_playing_button_index < len(self.play_buttons):
                self.play_buttons[self.current_playing_button_index].setStyleSheet("") # デフォルトに戻す
            
            # 現在再生するボタンの色を赤に変更
            self.play_buttons[index].setStyleSheet("background-color: red;")
            self.current_playing_button_index = index

            # プレイヤーウィンドウがなければ表示、あればスクリーンを切り替え
            if self.player_window is None:
                self.show_player_window()
            else:
                self.switch_screen()
            
            # ループ設定を適用
            loop_enabled = self.video_paths.get(index, {}).get('loop', False)
            self.media_player.setLoops(QMediaPlayer.Loops.Infinite if loop_enabled else 1)

            # ビデオを再生
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.media_player.play()
            self.current_playing_file_name = file_path.split('/')[-1]

    # 再生と一時停止を切り替えるメソッド
    def toggle_play_pause(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    # ビデオを停止するメソッド
    def stop_video(self):
        self.media_player.stop()
        self.time_label.setText("--:--:-- / --:--:--")
        self.current_playing_file_name = "停止中"
        self.current_video_label.setText(self.current_playing_file_name)
        # ボタンの色をリセット
        if self.current_playing_button_index != -1 and self.current_playing_button_index < len(self.play_buttons):
            self.play_buttons[self.current_playing_button_index].setStyleSheet("") # デフォルトに戻す
        self.current_playing_button_index = -1

    # プレイヤーウィンドウが閉じられたときの処理
    def player_window_closed(self):
        if self.media_player and self.media_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self.media_player.stop()
        self.player_window = None
        self.current_playing_file_name = "停止中"
        self.current_video_label.setText(self.current_playing_file_name)
        # ボタンの色をリセット
        if self.current_playing_button_index != -1 and self.current_playing_button_index < len(self.play_buttons):
            self.play_buttons[self.current_playing_button_index].setStyleSheet("") # デフォルトに戻す
        self.current_playing_button_index = -1

    # シークバーの位置を設定するメソッド
    def set_position(self, position):
        if self.media_player.source().isValid(): # 追加: 有効なソースがあるか確認
            self.media_player.setPosition(position)

    # 再生位置が変わったときの処理
    def position_changed(self, position):
        self.seek_slider.setValue(position)
        duration = self.media_player.duration()
        if duration > 0:
            remaining = duration - position
            # 時間ラベルを更新 (再生時間 / 総時間 (-残り時間))
            self.time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}  (-{self.format_time(remaining)})")

    # ビデオの総時間が変わったときの処理
    def duration_changed(self, duration):
        self.seek_slider.setRange(0, duration)
        self.time_label.setText(f"00:00:00 / {self.format_time(duration)}  (-{self.format_time(duration)})")

    # 再生状態の変更に応じてUIを更新するメソッド
    def update_play_pause_icon(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.current_video_label.setText(self.current_playing_file_name)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.current_video_label.setText(f"一時停止中: {self.current_playing_file_name}")
        else: # 停止状態
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.current_video_label.setText("停止中")

    # ミリ秒を hh:mm:ss 形式の文字列にフォーマットするメソッド
    def format_time(self, ms):
        seconds = round(ms / 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    # メディアプレーヤーでエラーが発生したときの処理
    def media_player_error(self, error):
        print(f"Error: {self.media_player.errorString()}")

    # ビデオのループ設定を切り替えるメソッド
    def toggle_video_loop_setting(self, index, state):
        if self.video_paths.get(index):
            self.video_paths[index]['loop'] = state # state は bool (True/False)
            
            # 現在再生中のビデオのループ設定が変更された場合、即座に適用
            if index == self.current_playing_button_index:
                self.media_player.setLoops(QMediaPlayer.Loops.Infinite if state else 1)