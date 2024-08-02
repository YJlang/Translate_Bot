# 필요한 라이브러리들을 가져옵니다.
import discord  # Discord와 연결하기 위한 라이브러리
from discord.ext import commands  # Discord 봇 명령어를 쉽게 만들기 위한 확장 기능
import speech_recognition as sr  # 음성을 텍스트로 변환하는 라이브러리
from googletrans import Translator  # 텍스트를 다른 언어로 번역하는 라이브러리
import pyttsx3  # 텍스트를 음성으로 변환하는 라이브러리
import pyaudio  # 오디오 입출력을 다루는 라이브러리
import wave  # 웨이브 오디오 파일을 다루는 라이브러리
import asyncio  # 비동기 프로그래밍을 위한 라이브러리
import io  # 입출력 작업을 위한 라이브러리
from gtts import gTTS  # Google의 텍스트 음성 변환 서비스를 사용하는 라이브러리
import tempfile  # 임시 파일을 만들고 사용하기 위한 라이브러리
import os  # 운영체제와 상호작용하기 위한 라이브러리

# Discord 봇이 사용할 권한을 설정합니다.
intents = discord.Intents.default()
intents.message_content = True  # 봇이 메시지 내용을 읽을 수 있게 합니다.

# 봇을 설정합니다. '!'를 명령어 앞에 붙이도록 지정합니다.
bot = commands.Bot(command_prefix='!', intents=intents)

# 음성 인식기를 설정합니다.
recognizer = sr.Recognizer()

# 번역기를 설정합니다.
translator = Translator()

# 봇이 준비되면 실행되는 함수입니다.
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')  # 봇이 성공적으로 연결되면 메시지를 출력합니다.

# '!translate' 명령어를 처리하는 함수입니다.
@bot.command()
async def translate(ctx, target_lang: str):
    await ctx.send(f"번역 모드를 시작합니다. 목표 언어: {target_lang}")
    await ctx.send("음성을 녹음하려면 '!record' 명령어를 사용하세요. '!stop'으로 번역 모드를 종료합니다.")

    while True:
        try:
            # 사용자의 다음 메시지를 기다립니다.
            msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author, timeout=60.0)
            
            if msg.content.lower() == '!stop':
                await ctx.send("번역 모드를 종료합니다.")
                break
            elif msg.content.lower() == '!record':
                await ctx.send("5초간 음성을 녹음합니다. 말씀해 주세요.")
                audio_data = record_audio()  # 음성을 녹음합니다.
                text = await recognize_speech(audio_data)  # 녹음된 음성을 텍스트로 변환합니다.
                
                if not text or text == "음성을 인식할 수 없습니다.":
                    await ctx.send("음성을 인식할 수 없습니다. 다시 시도해 주세요.")
                    continue

                translated = await translate_text(text, target_lang)  # 텍스트를 번역합니다.
                await send_translation(ctx, text, translated, target_lang)  # 번역 결과를 전송합니다.
            
        except asyncio.TimeoutError:
            await ctx.send("장시간 응답이 없어 번역 모드를 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {e}")
            await ctx.send(f"오류가 발생했습니다: {e}")
            break

# 음성을 녹음하는 함수입니다.
def record_audio(duration=5):
    CHUNK = 1024  # 한 번에 처리할 오디오 데이터의 크기
    FORMAT = pyaudio.paInt16  # 오디오 포맷 (16비트 정수)
    CHANNELS = 1  # 모노 채널
    RATE = 44100  # 샘플링 레이트 (1초당 44100개의 샘플)

    p = pyaudio.PyAudio()  # PyAudio 객체를 생성합니다.

    # 오디오 스트림을 엽니다.
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("녹음 중...")

    frames = []  # 녹음된 데이터를 저장할 리스트

    # 지정된 시간 동안 오디오를 녹음합니다.
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("녹음 완료.")

    # 스트림을 정리합니다.
    stream.stop_stream()
    stream.close()
    p.terminate()

    # 녹음된 데이터를 WAV 파일 형식으로 변환합니다.
    audio_data = io.BytesIO()
    wf = wave.open(audio_data, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    return audio_data.getvalue()

# 음성을 텍스트로 변환하는 함수입니다.
async def recognize_speech(audio_data):
    with sr.AudioFile(io.BytesIO(audio_data)) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio, language='ko-KR')  # Google의 음성 인식 서비스를 사용합니다.
    except sr.UnknownValueError:
        return "음성을 인식할 수 없습니다."
    except sr.RequestError as e:
        return f"음성 인식 서비스 오류: {e}"

# 텍스트를 번역하는 함수입니다.
async def translate_text(text, target_lang):
    translated = translator.translate(text, dest=target_lang)
    return translated.text

# 번역 결과를 전송하는 함수입니다.
async def send_translation(ctx, original, translated, target_lang):
    await ctx.send(f"원본: {original}\n번역: {translated}")
    
    # 번역된 텍스트를 음성으로 변환합니다.
    tts = gTTS(text=translated, lang=target_lang)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
        tts.save(fp.name)
        await ctx.send(file=discord.File(fp.name, 'translation.mp3'))
    os.unlink(fp.name)  # 임시 파일을 삭제합니다.

# 봇을 실행합니다.
bot.run('Token')