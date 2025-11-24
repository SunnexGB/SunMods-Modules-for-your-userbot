# requires: python-ffmpeg
# meta developer: @hSunnexGB
# meta repo: https://raw.githubusercontent.com/SunnexGB/SunMods-Modules-for-your-userbot/refs/heads/main/Alt-Circles.py

# Note
# This is a fork module from @KeyZenD.
# Here is a link to the original module: https://raw.githubusercontent.com/MuRuLOSE/limoka/refs/heads/main/KeyZenD/modules/Circles.py

from .. import loader, utils
from PIL import Image, ImageDraw, ImageOps, ImageFilter
import io
from telethon.tl.types import DocumentAttributeFilename
import subprocess
import json
import os

@loader.tds
class CirclesMod(loader.Module):
	"""rounds everything - reply to message"""
	strings = {
		"name": "Alt-Circles",
		"processing_image": "<b>Processing image</b><emoji document_id=5427181942934088912>💬</emoji>",
		"processing_video": "<b>Processing video</b><emoji document_id=5427181942934088912>💬</emoji>",
		"reply_prompt": "<b><emoji document_id=5260249440450520061>🤚</emoji>|Reply to image/sticker or video/gif!</b>",
		"saving_video": "<b>Saving video</b><emoji document_id=5427181942934088912>💬</emoji>",
		"ffprobe_failed": "<b><emoji document_id=5260249440450520061>🤚</emoji>|ffprobe failed to read the video. Is ffmpeg installed?</b>",
		"ffmpeg_failed": "<b><emoji document_id=5260249440450520061>🤚</emoji>|ffmpeg failed:</b> {error}",
	}

	strings_ru = {
		"name": "Alt-Circles",
        "_cls_doc": "Округляет всё - ответом на сообщение",
		"_cmd_doc_roundcmd": "round <Ответ на изображение/стикер или видео/gиф>",
        "processing_image": "<b>Обработка изображения</b><emoji document_id=5427181942934088912>💬</emoji>",
        "processing_video": "<b>Обработка видео</b><emoji document_id=5427181942934088912>💬</emoji>",
        "reply_prompt": "<b><emoji document_id=5260249440450520061>🤚</emoji>|Ответьте на изображение/стикер или видео/gif!</b>",
        "saving_video": "<b>Сохранение видео</b><emoji document_id=5427181942934088912>💬</emoji>",
        "ffmpeg_failed": "<b><emoji document_id=5260249440450520061>🤚</emoji>|ffmpeg завершился с ошибкой:</b> {error}",
	}

	def __init__(self):
		self.name = self.strings['name']
		
	async def client_ready(self, client, db):
		self.client = client
	
	@loader.sudo
	async def roundcmd(self, message):
		"""round <Reply to image/sticker or video/gif>"""
		reply = None
		if message.is_reply:
			reply = await message.get_reply_message()
			data = await check_media(reply)
			if isinstance(data, bool):
				await utils.answer(message, self.strings['reply_prompt'])
				return
		else:
			await utils.answer(message, self.strings['reply_prompt'])
			return
		data, type = data
		if type == "img":
			await message.edit(self.strings['processing_image'])
			img = io.BytesIO()
			bytes = await message.client.download_file(data, img)
			im = Image.open(img)
			w, h = im.size
			img = Image.new("RGBA", (w,h), (0,0,0,0))
			img.paste(im, (0, 0))
			m = min(w, h)
			img = img.crop(((w-m)//2, (h-m)//2, (w+m)//2, (h+m)//2))
			w, h = img.size
			mask = Image.new('L', (w, h), 0)
			draw = ImageDraw.Draw(mask) 
			draw.ellipse((10, 10, w-10, h-10), fill=255)
			mask = mask.filter(ImageFilter.GaussianBlur(2))
			img = ImageOps.fit(img, (w, h))
			img.putalpha(mask)
			im = io.BytesIO()
			im.name = "img.webp"
			img.save(im)
			im.seek(0)
			await message.client.send_file(message.to_id, im, reply_to=reply)
		else:
			await message.edit(self.strings['processing_video'])
			await message.client.download_file(data, "video.mp4")
			try:
				cmd = [
					'ffprobe', '-v', 'error', '-select_streams', 'v:0',
					'-show_entries', 'stream=width,height', '-of', 'json', 'video.mp4'
				]
				proc = subprocess.run(cmd, capture_output=True, text=True)
				if proc.returncode != 0:
					return
				info = json.loads(proc.stdout or '{}')
				streams = info.get('streams', [])
				if not streams:
					return
				w = int(streams[0].get('width', 0))
				h = int(streams[0].get('height', 0))
				m = min(w, h)
				x = (w - m) // 2
				y = (h - m) // 2
				await message.edit(self.strings['saving_video'])
				crop_filter = f"crop={m}:{m}:{x}:{y}"
				is_gif = getattr(reply, 'gif', False) or False
				if is_gif:
					cmd = [
						'ffmpeg', '-y', '-i', 'video.mp4',
						'-vf', crop_filter,
						'-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
						'-pix_fmt', 'yuv420p', '-an',
						'result.mp4'
					]
				else:
					cmd = [
						'ffmpeg', '-y', '-i', 'video.mp4',
						'-vf', crop_filter,
						'-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
						'-c:a', 'aac', '-strict', '-2',
						'result.mp4'
					]
				proc = subprocess.run(cmd, capture_output=True, text=True)
				if proc.returncode != 0:
					err = proc.stderr or ''
					lines = [l for l in err.splitlines() if l.strip()]
					filtered = []
					for l in lines:
						low = l.lower()
						if low.startswith('ffmpeg version') or low.startswith('built with') or low.startswith('configuration:'):
							continue
						filtered.append(l)
					if not filtered:
						safe = err[:300]
					else:
						safe = '\n'.join(filtered[-6:])
					await utils.answer(message, self.strings['ffmpeg_failed'].format(error=safe))
					return
				await message.client.send_file(message.to_id, 'result.mp4', video_note=(not is_gif), reply_to=reply)
			finally:
				if os.path.exists('video.mp4'):
					os.remove('video.mp4')
				if os.path.exists('result.mp4'):
					os.remove('result.mp4')
		await message.delete()
			
	
async def check_media(reply):
	type = "img"
	if reply and reply.media:
		if reply.photo:
			data = reply.photo
		elif reply.document:
			if DocumentAttributeFilename(file_name='AnimatedSticker.tgs') in reply.media.document.attributes:
				return False
			if reply.gif or reply.video:
				type = "vid"
			if reply.audio or reply.voice:
				return False
			data = reply.media.document
		else:
			return False
	else:
		return False

	if not data or data is None:
		return False
	else:
		return (data, type)
