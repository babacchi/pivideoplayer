
import threading
import io
import sys
import textwrap
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtMultimedia import QMediaPlayer
from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.Transport.Transport import TransportError

TIME_DISPLAY_KEY = 9
PAUSE_KEY = 10

class StreamDeckHandler(QObject):
    key_pressed = pyqtSignal(int)
    pause_key_pressed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.opened_decks = []
        self.key_states = {i: {'text': "", 'playing': False} for i in range(9)}
        self.deck = None
        self.playback_state = QMediaPlayer.PlaybackState.StoppedState
        self.last_position = 0
        self.last_duration = 0

        self.streamdeck_thread = threading.Thread(target=self.init_streamdeck)
        self.streamdeck_thread.daemon = True
        self.streamdeck_thread.start()

    def cleanup(self):
        for deck in self.opened_decks:
            with deck:
                deck.reset()
                deck.close()
        print("Stream Decks released.")

    @pyqtSlot(int, str)
    def update_key_with_filename(self, key_index, filename):
        if 0 <= key_index < 9:
            self.key_states[key_index]['text'] = filename
            self._redraw_key(key_index)

    @pyqtSlot(int, bool)
    def update_key_playback_state(self, key_index, is_playing):
        if 0 <= key_index < 9:
            self.key_states[key_index]['playing'] = is_playing
            self._redraw_key(key_index)

            any_video_playing = any(s['playing'] for s in self.key_states.values())
            if not any_video_playing:
                self._clear_time_display()

    @pyqtSlot(QMediaPlayer.PlaybackState)
    def update_global_playback_state(self, state):
        self.playback_state = state
        self._redraw_pause_key()  # Redraw pause key on any state change
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self._clear_time_display()
            self._clear_pause_key()
        else:
            # Time display is handled by position updates, but we need to draw it once when pausing.
            self._redraw_time_display(self.last_position, self.last_duration)

    @pyqtSlot(int, int, int)
    def update_time_display(self, key_index, position, duration):
        self.last_position = position
        self.last_duration = duration
        self._redraw_time_display(position, duration)

    def _redraw_key(self, key):
        if not self.deck:
            return

        state = self.key_states.get(key)
        if not state:
            return

        bg_color = "red" if state['playing'] else "black"
        number = str(key + 1)

        image = self.render_key_image(self.deck, number, state['text'], bg_color)
        self._send_image_to_key(key, image)

    def _redraw_time_display(self, position, duration):
        if not self.deck or self.deck.key_count() <= TIME_DISPLAY_KEY:
            return
        image = self.render_time_display_image(self.deck, position, duration)
        self._send_image_to_key(TIME_DISPLAY_KEY, image)

    def _clear_time_display(self):
        if not self.deck or self.deck.key_count() <= TIME_DISPLAY_KEY:
            return
        image = Image.new("RGB", self.deck.key_image_format()['size'], "black")
        self._send_image_to_key(TIME_DISPLAY_KEY, image)

    def _redraw_pause_key(self):
        if not self.deck or self.deck.key_count() <= PAUSE_KEY:
            return
        image = self.render_pause_key_image(self.deck)
        self._send_image_to_key(PAUSE_KEY, image)

    def render_pause_key_image(self, deck):
        image = Image.new("RGB", deck.key_image_format()['size'], "black")
        draw = ImageDraw.Draw(image)
        
        width, height = deck.key_image_format()['size']
        center_x, center_y = width / 2, height / 2
        
        icon_color = "white"

        if self.playback_state == QMediaPlayer.PlaybackState.PlayingState:
            # Draw Pause icon (two vertical bars)
            bar_width = width / 6
            bar_height = height / 2
            gap = bar_width / 2
            
            x0_left = center_x - gap - bar_width
            y0 = center_y - bar_height / 2
            x1_left = center_x - gap
            y1 = center_y + bar_height / 2
            draw.rectangle([x0_left, y0, x1_left, y1], fill=icon_color)
            
            x0_right = center_x + gap
            x1_right = center_x + gap + bar_width
            draw.rectangle([x0_right, y0, x1_right, y1], fill=icon_color)

        elif self.playback_state == QMediaPlayer.PlaybackState.PausedState:
            # Draw Play icon (a triangle)
            triangle_height = height / 2
            triangle_width = triangle_height * 0.866  # Equilateral-ish
            
            x0 = center_x - triangle_width / 3
            y0 = center_y - triangle_height / 2
            
            x1 = x0
            y1 = center_y + triangle_height / 2
            
            x2 = center_x + (triangle_width * 2 / 3)
            y2 = center_y
            
            draw.polygon([(x0, y0), (x1, y1), (x2, y2)], fill=icon_color)

        return image

    def _clear_pause_key(self):
        if not self.deck or self.deck.key_count() <= PAUSE_KEY:
            return
        image = Image.new("RGB", self.deck.key_image_format()['size'], "black")
        self._send_image_to_key(PAUSE_KEY, image)

    def _send_image_to_key(self, key, image):
        if not self.deck:
            return
        try:
            key_format = self.deck.key_image_format()
            image_format = key_format['format']
            flip_x, flip_y = key_format['flip']
            rotation = key_format['rotation']

            if flip_x:
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
            if flip_y:
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
            if rotation != 0:
                image = image.rotate(rotation)

            with io.BytesIO() as buff:
                image.save(buff, format=image_format.lower())
                self.deck.set_key_image(key, buff.getvalue())
        except TransportError as e:
            print(f"Lost connection to Stream Deck: {e}")
            print("Please restart the application to reconnect.")
            self.deck = None

    def render_key_image(self, deck, number_text, filename_text, bg_color="black"):
        # (Same as before, but without time display)
        if sys.platform == "win32":
            jp_font_path = "C:/Windows/Fonts/meiryo.ttc"
            en_font_path = "C:/Windows/Fonts/arial.ttf"
        elif sys.platform == "darwin":
            jp_font_path = "/System/Library/Fonts/Supplemental/ヒラギノ角ゴシック W3.ttc"
            en_font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
        else:  # Linux
            jp_font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
            en_font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

        image = Image.new("RGB", deck.key_image_format()['size'], bg_color)
        draw = ImageDraw.Draw(image)

        try:
            num_font = ImageFont.truetype(jp_font_path, 24, index=0)
            file_font = ImageFont.truetype(jp_font_path, 14, index=0)
            large_font = ImageFont.truetype(jp_font_path, 48, index=0)
        except IOError:
            try:
                num_font = ImageFont.truetype(en_font_path, 24)
                file_font = ImageFont.truetype(en_font_path, 14)
                large_font = ImageFont.truetype(en_font_path, 48)
            except IOError:
                num_font = ImageFont.load_default()
                file_font = ImageFont.load_default()
                large_font = ImageFont.load_default()

        if not filename_text:
            draw.text((image.width / 2, 5), text=number_text, font=num_font, anchor="ma", fill="white")
        else:
            draw.text((image.width / 2, 5), text=number_text, font=num_font, anchor="ma", fill="white")
            wrapper = textwrap.TextWrapper(width=12)
            lines = wrapper.wrap(text=filename_text)
            y = 30
            for line in lines:
                draw.text((5, y), text=line, font=file_font, fill="white")
                bbox = file_font.getbbox(line)
                y += bbox[3] + 2
        return image

    # ミリ秒を hh:mm:ss 形式の文字列にフォーマットするメソッド
    def format_time(self, ms):
        seconds = round(ms / 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    
    def render_time_display_image(self, deck, position, duration):
        if sys.platform == "win32":
            jp_font_path = "C:/Windows/Fonts/meiryo.ttc"
            en_font_path = "C:/Windows/Fonts/arial.ttf"
        elif sys.platform == "darwin":
            jp_font_path = "/System/Library/Fonts/Supplemental/ヒラギノ角ゴシック W3.ttc"
            en_font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
        else:  # Linux
            jp_font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
            en_font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
            
        image = Image.new("RGB", deck.key_image_format()['size'], "black")
        draw = ImageDraw.Draw(image)
        try:
            time_font = ImageFont.truetype(jp_font_path, 13, index=0)
        except IOError:
            try:
                time_font = ImageFont.truetype(en_font_path, 13)
            except IOError:
                time_font = ImageFont.load_default()

        pos_text = self.format_time(position)
        rem_text = self.format_time(duration - position)
        
        draw.text((deck.key_image_format()['size'][0] / 2, 35), text=pos_text, font=time_font, anchor="ms", fill="white")
        draw.text((deck.key_image_format()['size'][0] / 2, 65), text=f"-{rem_text}", font=time_font, anchor="ms", fill="white")
        return image

    def init_streamdeck(self):
        streamdecks = DeviceManager().enumerate()
        if not streamdecks:
            print("No Stream Deck found.")
            return

        self.deck = streamdecks[0]
        self.configure_deck(self.deck)

    def configure_deck(self, deck):
        try:
            deck.open()
            self.opened_decks.append(deck)
        except TransportError:
            print(f"Could not open Stream Deck '{deck.id()}'. It might be in use by another application or permissions are missing.")
            self.deck = None
            return

        with deck:
            deck.reset()
            deck.set_brightness(50)

        for key in range(9):
            self._redraw_key(key)
        
        self._clear_time_display()
        self._clear_pause_key()

        deck.set_key_callback(self.key_change_callback)

    def key_change_callback(self, deck, key, state):
        if state:
            if 0 <= key <= 8:
                self.key_pressed.emit(key)
            elif key == PAUSE_KEY:
                self.pause_key_pressed.emit()

