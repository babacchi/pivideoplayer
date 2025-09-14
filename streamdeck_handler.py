
import threading
import io
import sys
import textwrap
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.Transport.Transport import TransportError

class StreamDeckHandler(QObject):
    key_pressed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.opened_decks = []
        self.key_states = {i: {'text': "", 'playing': False} for i in range(9)}
        self.deck = None  # Assume one deck for simplicity

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

    def _redraw_key(self, key):
        if not self.deck:
            return

        state = self.key_states.get(key, {'text': '', 'playing': False})
        filename = state['text']
        bg_color = "red" if state['playing'] else "black"
        number = str(key + 1)

        image = self.render_key_image(self.deck, number, filename, bg_color)
        
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

    def render_key_image(self, deck, number_text, filename_text, bg_color="black"):
        if sys.platform == "win32":
            jp_font_path = "C:/Windows/Fonts/meiryo.ttc"
            en_font_path = "C:/Windows/Fonts/arial.ttf"
        elif sys.platform == "darwin":
            jp_font_path = "/System/Library/Fonts/Supplemental/ヒラギノ角ゴシック W3.ttc"
            en_font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
        else:  # Linux or other
            jp_font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
            en_font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

        image = Image.new("RGB", deck.key_image_format()['size'], bg_color)
        draw = ImageDraw.Draw(image)

        try:
            num_font = ImageFont.truetype(jp_font_path, 20, index=0)
            file_font = ImageFont.truetype(jp_font_path, 12, index=0)
        except IOError:
            try:
                num_font = ImageFont.truetype(en_font_path, 20)
                file_font = ImageFont.truetype(en_font_path, 12)
            except IOError:
                num_font = ImageFont.load_default()
                file_font = ImageFont.load_default()
        # 数字の描画
        draw.text((image.width / 2, 5), text=number_text, font=num_font, anchor="mt", fill="white")
        if filename_text:
            # Filename below, left-aligned and wrapped
            wrapper = textwrap.TextWrapper(width=12)  # Adjust width as needed
            lines = wrapper.wrap(text=filename_text)
            
            y = 20  # Starting y for filename
            for line in lines:
                draw.text((5, y), text=line, font=file_font, fill="white")
                bbox = file_font.getbbox(line)
                y += bbox[3] + 1  # Advance y by line height + padding

        return image

    def init_streamdeck(self):
        streamdecks = DeviceManager().enumerate()
        if not streamdecks:
            print("No Stream Deck found.")
            return

        # Use the first deck found.
        self.deck = streamdecks[0]
        self.configure_deck(self.deck)

    def configure_deck(self, deck):
        try:
            deck.open()
            self.opened_decks.append(deck)
        except TransportError:
            print(f"Could not open Stream Deck '{deck.id()}'. It might be in use by another application or permissions are missing.")
            self.deck = None  # Failed to open
            return

        with deck:
            deck.reset()
            deck.set_brightness(50)

        for key in range(9):
            self._redraw_key(key)

        deck.set_key_callback(self.key_change_callback)

    def key_change_callback(self, deck, key, state):
        if state:  # Key pressed
            if 0 <= key <= 8:
                self.key_pressed.emit(key)

