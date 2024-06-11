import discord
import openai
from discord.ext import commands
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

GPT = "GPTのAPIキー"
client = openai.Client(api_key=GPT)

BOT_TOKEN = "BOTトークン"

tables = str.maketrans(
    "！＃＄％＆＇（）＊＋，－．／０１２３４５６７８９：；＜＝＞？＠ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ［＼］＾＿｀>？＠ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ｛｜｝～　",
    "!#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`>?@abcdefghijklmnopqrstuvwxyz{|}~ ",
)

premium_sessions = {}
active_channels = {}
conversation_history = {}

@bot.event
async def on_message(message: discord.Message):
    message.content = message.content.translate(tables)
    if message.author.bot:
        return

    session = premium_sessions.get(message.channel.id)
    if session and session['user_id'] == message.author.id:
        await handle_gpt_message(message, message.content)

async def handle_gpt_message(message: discord.Message, gprompt: str):
    try:
        session = premium_sessions.get(message.channel.id)
        if not session or session['user_id'] != message.author.id:
            return

        await message.channel.send("回答を待っています...", mention_author=False)
        conversation_id = f"{message.channel.id}-{message.author.id}"
        conversation_history.setdefault(conversation_id, [])

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは日本語で回答するAIです。"},
                *conversation_history[conversation_id],
                {"role": "user", "content": gprompt}
            ]
        )
        gkun = response.choices[0].message.content.strip()
        conversation_history[conversation_id].extend([
            {"role": "user", "content": gprompt},
            {"role": "assistant", "content": gkun}
        ])

        await message.channel.send(f"{gprompt}\n\n>> {gkun}", mention_author=False)
        logger.info(f"User prompt: {gprompt}")
        logger.info(f"GPT-3 response: {gkun}")
        logger.info(f"Remaining tokens: {response.usage.total_tokens}")

    except Exception as e:
        await message.reply(f"エラー\n{e}", mention_author=False)
        logger.error(f"Error: {e}")

@bot.tree.command(name="startgpt", description="chatGPTとの会話専用チャンネルを作成します")
async def startgpt(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    
    if active_channels.get((guild_id, user_id)):
        await interaction.response.send_message("既にGPT専用チャンネルが存在します。", ephemeral=True)
        return

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    channel = await interaction.guild.create_text_channel(name=f'gpt-{interaction.user.name}', overwrites=overwrites)
    
    premium_sessions[channel.id] = {'user_id': user_id}
    active_channels[(guild_id, user_id)] = channel.id
    
    await interaction.response.send_message(f"GPT専用チャンネルを作成しました: {channel.mention}", ephemeral=True)
    logger.info(f"{user_id}が{guild_id}でGPTチャンネルを作成しました")

@bot.tree.command(name="gptend", description="GPT-3との対話専用チャンネルを削除します")
async def gptend(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild.id
    channel_id = active_channels.get((guild_id, user_id))
    
    if channel_id:
        channel = bot.get_channel(channel_id)
        await channel.delete()
        del premium_sessions[channel_id]
        del active_channels[(guild_id, user_id)]
        await interaction.response.send_message("GPT専用チャンネルを削除しました。", ephemeral=True)
        logger.info(f"{user_id}が{guild_id}でgptを終了しました")
    else:
        await interaction.response.send_message("現在開かれているなGPT専用チャンネルはありません。", ephemeral=True)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='みんなのこと'))
    print(f'{bot.user}が起動したよ！')
    await bot.tree.sync()


bot.run(BOT_TOKEN)