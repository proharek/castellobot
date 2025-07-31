from discord import Interaction, Embed, ButtonStyle
from discord.ui import View, button
from discord.ext import commands
from core.database_supabase import set_user_language, get_user_language
from core.language import LanguageManager

lang_manager = LanguageManager()

class LanguageView(View):
    def __init__(self, user_id: int, lang: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.lang = lang

    @button(label="Русский", style=ButtonStyle.primary)
    async def set_ru(self, interaction: Interaction, button):
        await set_user_language(self.user_id, "ru")
        try:
            await interaction.response.edit_message(
                content=lang_manager.get_text("language_set_ru", "ru"), view=None
            )
        except discord.errors.NotFound:
            pass

    @button(label="Українська 🇺🇦", style=ButtonStyle.secondary)
    async def set_ua(self, interaction: Interaction, button):
        await set_user_language(self.user_id, "ua")
        try:
            await interaction.response.edit_message(
                content=lang_manager.get_text("language_set_ua", "ua"), view=None
            )
        except discord.errors.NotFound:
            pass

@bot.tree.command(name="language", description="Сменить язык интерфейса")
async def language(interaction: Interaction):
    user_id = interaction.user.id
    lang = await get_user_language(user_id) or "ru"

    embed = Embed(
        title=lang_manager.get_text("select_language", lang),
        color=0x2b2d31
    )

    try:
        await interaction.response.send_message(embed=embed, view=LanguageView(user_id, lang), ephemeral=True)
    except discord.errors.NotFound:
        pass


