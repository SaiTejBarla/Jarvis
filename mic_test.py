import pyaudio, array

pa = pyaudio.PyAudio()
s = pa.open(rate=16000, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=1024)
print("Speak now (10 seconds)... watch the RMS values")
print("-" * 50)
for _ in range(160):
    d = s.read(1024, exception_on_overflow=False)
    rms = (sum(x*x for x in array.array("h", d)) / len(array.array("h", d))) ** 0.5
    bar = "#" * int(rms / 20)
    print(f"RMS: {rms:6.1f}  {bar}")
s.stop_stream()
s.close()
pa.terminate()
print("-" * 50)
print("Done.")
