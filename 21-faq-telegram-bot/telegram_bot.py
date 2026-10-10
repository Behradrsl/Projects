"""Serve FAQ replies using Telegram polling."""

import asyncio
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from faq import answer_question

logger = logging.getLogger(__name__)


def build_application(token: str, records: list[dict], use_ai=False):
    application = Application.builder().token(token).build()

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_message:
            await update.effective_message.reply_text(
                (
                    "Ask a question about the service. I answer from the "
                    "configured FAQ. Use /help for examples."
                )
            )

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        examples = "\n".join("- " + record["question"] for record in records[:6])
        if update.effective_message:
            await update.effective_message.reply_text(
                "Try one of these questions:\n" + examples
            )

    async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_message or not update.effective_message.text:
            return
        try:
            text = await asyncio.to_thread(
                answer_question, update.effective_message.text, records, use_ai
            )
        except (ValueError, RuntimeError) as error:
            text = str(error)
        await update.effective_message.reply_text(text)

    async def on_error(update, context: ContextTypes.DEFAULT_TYPE):
        # Avoid logging URLs or exception objects that could contain the bot token.
        logger.warning("Telegram update failed (%s).", type(context.error).__name__)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    application.add_error_handler(on_error)
    return application
