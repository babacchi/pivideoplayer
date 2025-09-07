import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QGridLayout, QWidget, QFileDialog, QHBoxLayout, QVBoxLayout, QSlider, QStyle, QComboBox, QLabel, QMenuBar, QMenu, QSizePolicy, QCheckBox
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QKeyEvent, QCloseEvent


class PlayerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: black;")
        self.video_widget = QVideoWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_widget)
        self.setLayout(layout)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Player Controller")
        self.setGeometry(100, 100, 800, 200)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self.create_menu()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.controls_layout = QHBoxLayout()
        self.main_layout.addLayout(self.controls_layout)

        self.play_pause_button = QPushButton()
        self.play_pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.controls_layout.addWidget(self.play_pause_button)

        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_video)
        self.controls_layout.addWidget(self.stop_button)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.sliderMoved.connect(self.set_position)
        self.seek_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred) # シークバーを拡張
        self.controls_layout.addWidget(self.seek_slider)

        self.time_label = QLabel("--:--:-- / --:--:--")
        self.time_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
        self.time_label.setFixedWidth(400) # 固定幅を設定
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter) # 右揃えと垂直中央揃え
        self.controls_layout.addWidget(self.time_label)

        self.grid_layout = QGridLayout()
        self.main_layout.addLayout(self.grid_layout)

        # Output Monitor Selector
        screen_selector_layout = QHBoxLayout()
        screen_selector_layout.setSpacing(0)
        screen_selector_layout.setContentsMargins(0, 0, 0, 0)
        screen_selector_layout.addWidget(QLabel("出力モニタ:"))
        self.screens = QApplication.screens()
        self.screen_selector = QComboBox()
        self.screen_selector.addItems([screen.name() or f"Screen {i + 1}" for i, screen in enumerate(self.screens)])
        self.screen_selector.currentIndexChanged.connect(self.switch_screen)
        screen_selector_layout.addWidget(self.screen_selector)
        self.main_layout.addLayout(screen_selector_layout)

        # Audio Output Selector
        self.audio_devices = QMediaDevices.audioOutputs()
        audio_selector_layout = QHBoxLayout()
        audio_selector_layout.setSpacing(0)
        audio_selector_layout.setContentsMargins(0, 0, 0, 0)
        audio_selector_layout.addWidget(QLabel("音声出力先:"))
        self.audio_selector = QComboBox()
        self.audio_selector.addItems([device.description() for device in self.audio_devices])
        self.audio_selector.currentIndexChanged.connect(self.switch_audio_device)
        audio_selector_layout.addWidget(self.audio_selector)
        self.main_layout.addLayout(audio_selector_layout)

        self.video_paths = {}
        self.play_buttons = [] # Store references to play buttons
        self.loop_checkboxes = [] # Store references to loop checkboxes
        self.current_playing_button_index = -1 # Track currently playing button
        self.create_buttons()

        self.current_playing_file_name = "停止中"
        self.current_video_label = QLabel(self.current_playing_file_name)
        self.main_layout.addWidget(self.current_video_label)

        self.player_window = None
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.switch_audio_device(self.audio_selector.currentIndex())

        self.media_player.errorOccurred.connect(self.media_player_error)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.playbackStateChanged.connect(self.update_play_pause_icon)

        self.show_player_window()

        self.set_font_size("medium") # Set default font size

    def create_menu(self):
        menubar = self.menuBar()
        view_menu = menubar.addMenu("表示")

        small_font_action = view_menu.addAction("小")
        small_font_action.triggered.connect(lambda: self.set_font_size("small"))

        medium_font_action = view_menu.addAction("中")
        medium_font_action.triggered.connect(lambda: self.set_font_size("medium"))

        large_font_action = view_menu.addAction("大")
        large_font_action.triggered.connect(lambda: self.set_font_size("large"))

    def set_font_size(self, size):
        if size == "small":
            font_size = 10
        elif size == "medium":
            font_size = 12
        elif size == "large":
            font_size = 14
        else:
            font_size = 12 # Default to medium

        QApplication.instance().setStyleSheet(f"* {{ font-size: {font_size}pt; }}")

    def create_buttons(self):
        for i in range(9):
            row = i // 3
            base_col = (i % 3) * 3  # 各スロットに3列使う

            play_button = QPushButton(f"Load Video {i + 1}")
            play_button.clicked.connect(lambda checked, idx=i: self.play_video_from_button(idx))
            play_button.setEnabled(False)
            self.grid_layout.addWidget(play_button, row, base_col)
            self.play_buttons.append(play_button)

            load_button = QPushButton("...")
            load_button.setFixedWidth(30)
            load_button.clicked.connect(lambda checked, b=play_button, idx=i: self.load_video(b, idx))
            self.grid_layout.addWidget(load_button, row, base_col + 1)

            loop_checkbox = QCheckBox("ループ")
            loop_checkbox.toggled.connect(lambda checked, idx=i: self.toggle_video_loop_setting(idx, checked))
            self.grid_layout.addWidget(loop_checkbox, row, base_col + 2)
            self.loop_checkboxes.append(loop_checkbox)

            self.video_paths[i] = {'path': None, 'loop': False}

    def closeEvent(self, event: QCloseEvent):
        if self.player_window and self.player_window.isVisible():
            self.player_window.close()
        event.accept()

    def show_player_window(self):
        if self.player_window is None:
            screen_index = self.screen_selector.currentIndex()
            screen = self.screens[screen_index] if 0 <= screen_index < len(self.screens) else QApplication.primaryScreen()
            
            self.player_window = PlayerWindow()
            self.player_window.destroyed.connect(self.player_window_closed)
            self.media_player.setVideoOutput(self.player_window.video_widget)
            
            self.player_window.setGeometry(screen.geometry())
            self.player_window.showFullScreen()

    def switch_screen(self):
        if self.player_window:
            screen_index = self.screen_selector.currentIndex()
            screen = self.screens[screen_index] if 0 <= screen_index < len(self.screens) else QApplication.primaryScreen()

            if self.player_window.screen() != screen:
                # Preserve state
                current_source = self.media_player.source()
                current_position = self.media_player.position()
                is_playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                is_looping = self.media_player.loops() == QMediaPlayer.Loops.Infinite

                # Disconnect from old window and destroy it
                self.media_player.setVideoOutput(None)
                try:
                    self.player_window.destroyed.disconnect(self.player_window_closed)
                except TypeError:
                    # This can happen if the connection was already broken
                    pass
                self.player_window.close()
                self.player_window.deleteLater()
                
                # Create new window
                self.player_window = PlayerWindow()
                self.player_window.destroyed.connect(self.player_window_closed)
                self.media_player.setVideoOutput(self.player_window.video_widget)
                self.player_window.setGeometry(screen.geometry())
                self.player_window.showFullScreen()

                # Restore state
                if current_source.isValid():
                    self.media_player.setSource(current_source)
                    self.media_player.setLoops(QMediaPlayer.Loops.Infinite if is_looping else 1)
                    self.media_player.setPosition(current_position)
                    if is_playing:
                        self.media_player.play()

    def switch_audio_device(self, index):
        if 0 <= index < len(self.audio_devices):
            self.audio_output.setDevice(self.audio_devices[index])

    def load_video(self, button, index):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Video", "", "Video Files (*.mp4 *.avi *.mkv)")
        if file_path:
            self.video_paths[index]['path'] = file_path
            filename = file_path.split('/')[-1]
            button.setToolTip(filename)
            max_len = 25
            if len(filename) > max_len:
                display_name = filename[:max_len-3] + "..."
            else:
                display_name = filename
            button.setText(display_name)
            button.setEnabled(True)
            if self.player_window is None:
                self.show_player_window()
            else:
                self.switch_screen()

    def play_video_from_button(self, index):
        file_path = self.video_paths.get(index, {}).get('path')
        if file_path:
            # Reset previous button color
            if self.current_playing_button_index != -1 and self.current_playing_button_index < len(self.play_buttons):
                self.play_buttons[self.current_playing_button_index].setStyleSheet("") # Reset to default
            
            # Set new button color to red
            self.play_buttons[index].setStyleSheet("background-color: red;")
            self.current_playing_button_index = index

            if self.player_window is None:
                self.show_player_window()
            else:
                self.switch_screen()
            loop_enabled = self.video_paths.get(index, {}).get('loop', False)
            self.media_player.setLoops(QMediaPlayer.Loops.Infinite if loop_enabled else 1)

            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.media_player.play()
            self.current_playing_file_name = file_path.split('/')[-1]

    def toggle_play_pause(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def stop_video(self):
        self.media_player.stop()
        self.time_label.setText("--:--:-- / --:--:--")
        self.current_playing_file_name = "停止中"
        self.current_video_label.setText(self.current_playing_file_name)
        # Reset button color on stop
        if self.current_playing_button_index != -1 and self.current_playing_button_index < len(self.play_buttons):
            self.play_buttons[self.current_playing_button_index].setStyleSheet("") # Reset to default
        self.current_playing_button_index = -1

    def player_window_closed(self):
        # Check if media_player is still a valid object before accessing it
        if self.media_player and self.media_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self.media_player.stop()
        self.player_window = None
        self.current_playing_file_name = "停止中"
        self.current_video_label.setText(self.current_playing_file_name)
        # Reset button color on window close
        if self.current_playing_button_index != -1 and self.current_playing_button_index < len(self.play_buttons):
            self.play_buttons[self.current_playing_button_index].setStyleSheet("") # Reset to default
        self.current_playing_button_index = -1

    def set_position(self, position):
        self.media_player.setPosition(position)

    def position_changed(self, position):
        self.seek_slider.setValue(position)
        duration = self.media_player.duration()
        if duration > 0:
            remaining = duration - position
            self.time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}  (-{self.format_time(remaining)})")

    def duration_changed(self, duration):
        self.seek_slider.setRange(0, duration)
        self.time_label.setText(f"00:00:00 / {self.format_time(duration)}  (-{self.format_time(duration)})")

    def update_play_pause_icon(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.current_video_label.setText(self.current_playing_file_name)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.current_video_label.setText(f"一時停止中: {self.current_playing_file_name}")
        else:
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.current_video_label.setText("停止中")

    def format_time(self, ms):
        seconds = round(ms / 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def media_player_error(self, error):
        print(f"Error: {self.media_player.errorString()}")

    def toggle_video_loop_setting(self, index, state):
        if self.video_paths.get(index):
            # state は bool（True か False）
            self.video_paths[index]['loop'] = state

            if index == self.current_playing_button_index:
                self.media_player.setLoops(QMediaPlayer.Loops.Infinite if state else 1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = VideoPlayer()
    controller.show()
    sys.exit(app.exec())
