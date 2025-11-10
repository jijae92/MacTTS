from localkoreantts import audio_io


def test_dummy_sounddevice_fixture_prevents_real_play():
    # The auto-use fixture replaces sounddevice with a dummy that records calls.
    assert hasattr(audio_io.sd, "play_calls")
    audio_io.sd.play([0.0, 0.1], samplerate=1, device="dummy")
    audio_io.sd.wait()
    assert audio_io.sd.play_calls
