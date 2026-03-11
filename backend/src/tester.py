from src.audio_tester import AudioTester
from src.clip_audio import AudioClipper

AudioClipper().run()
AudioTester(one_by_one=True).run()