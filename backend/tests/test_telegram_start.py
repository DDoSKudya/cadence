from apps.telegram_bot.bot import build_start_reply


def test_build_start_reply_private_chat():
    text = build_start_reply(chat_id=597181229, chat_type="private")
    assert "597181229" in text
    assert "Личный чат" in text
    assert "user" in text


def test_build_start_reply_group_chat():
    text = build_start_reply(chat_id=-1001234567890, chat_type="supergroup")
    assert "-1001234567890" in text
    assert "Группа" in text
    assert "group" in text
