"""The unseen pack layout is unknown: splitting must work for common layouts (invented texts)."""
from reader import split_messages


def test_blank_line_blocks_with_headers_stay_whole():
    t = "Message 1\nFrom: Registrar\nDate: 2 Dec\nBudget is Rs 5.\n\nMessage 2\nFrom: Hall\nDate: 1 Dec\nRoom seats 9."
    out = split_messages(t)
    assert len(out) == 2 and out[0].startswith("Message 1") and "Budget" in out[0]


def test_numbered_without_blank_lines():
    t = "1. Registrar, email, 2 Dec: budget Rs 5.\n2. Hall, email, 1 Dec: room seats 9.\n3) Caterer: box Rs 3."
    assert len(split_messages(t)) == 3


def test_bracket_numbers_with_continuation_lines():
    t = "[1] Registrar — 2 Dec\nBudget is Rs 5.\n[2] Hall — 1 Dec\nRoom seats 9.\nAlso has AC."
    out = split_messages(t)
    assert len(out) == 2 and "Also has AC." in out[1]


def test_from_headers_without_blank_lines():
    t = "From: Registrar\nDate: 2 Dec\nBudget is Rs 5.\nFrom: Hall\nDate: 1 Dec\nRoom seats 9."
    out = split_messages(t)
    assert len(out) == 2 and out[1].startswith("From: Hall")


def test_whatsapp_export_lines():
    t = "12/11/26, 10:30 - Ali: lunch ab 900 ka hai\n12/11/26, 10:35 - Sara: theek hai\n13/11/26, 09:00 - Ali: delivery free"
    assert len(split_messages(t)) == 3


def test_chat_lines_name_colon():
    t = "Caterer: box ab Rs 900\nDean: budget Rs 400,000\nJudge lead: 8 judges confirmed"
    assert len(split_messages(t)) == 3


def test_markdown_table_rows():
    t = ("| # | From | Date | Message |\n|---|---|---|---|\n| 1 | Dean, email | 9 Dec | \"Budget Rs 5\" |\n"
         "| 2 | Hall, email | 3 Dec | \"Room seats 9\" |")
    out = split_messages(t)
    assert len(out) == 2 and "Dean" in out[0]


def test_single_multiline_email_not_split():
    t = "Dear team,\nThe printing bill came in higher.\nIt is now Rs 15,500.\nRegards, Accounts"
    assert split_messages(t) == [t]


def test_numbered_list_inside_one_email_not_split():
    t = "Accounts, email, 2 Dec\nAlready ordered:\n1. trophies Rs 45,000\n2. t-shirts Rs 60,000"
    assert split_messages(t) == [t]


def test_numbered_list_inside_blank_line_pack_not_split():
    t = "Dean: budget Rs 9.\n\nAccounts: ordered\n1. cups Rs 5\n2. pens Rs 6\n\nHall: seats 50."
    out = split_messages(t)
    assert len(out) == 3 and "pens" in out[1]
