import streamlit as st
import sqlite3
import random
from datetime import datetime
import os
import csv
import io

# --- データベース設定 ---
DB_NAME = os.path.join(os.path.dirname(__file__), "words.db")

def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            meaning TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode TEXT,
            correct INTEGER,
            total INTEGER,
            percent REAL,
            played_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_word(word, meaning):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT INTO words (word, meaning) VALUES (?, ?)", (word, meaning))
    conn.commit()
    conn.close()

def get_all_words():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, word, meaning FROM words")
    data = cur.fetchall()
    conn.close()
    return data

def delete_word(word_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM words WHERE id = ?", (word_id,))
    conn.commit()
    conn.close()

def save_result(mode, correct, total):
    percent = round(correct / total * 100, 1) if total > 0 else 0.0
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO results (mode, correct, total, percent, played_at) VALUES (?, ?, ?, ?, ?)",
        (mode, correct, total, percent, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()

def get_results():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT mode, correct, total, percent, played_at FROM results ORDER BY id DESC LIMIT 30"
    )
    data = cur.fetchall()
    conn.close()
    return data

# --- CSV取り込み ---
def import_words_from_csv(file):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    text = file.getvalue().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))

    count = 0
    for row in reader:
        if len(row) >= 2:
            word = row[0].strip()
            meaning = row[1].strip()
            if word and meaning:
                cur.execute(
                    "INSERT INTO words (word, meaning) VALUES (?, ?)",
                    (word, meaning)
                )
                count += 1

    conn.commit()
    conn.close()
    return count

# --- Streamlit ---
st.set_page_config(page_title="英単語クイズアプリ", page_icon="🧠")
st.title("🧠 英単語クイズアプリ")

create_tables()

menu = st.sidebar.radio("メニュー", [
    "単語を追加",
    "CSV取り込み",
    "単語一覧・削除",
    "1問クイズ",
    "5問クイズ",
    "全単語クイズ",
    "実績を見る",
    "ヘルプ"
])

# --- クイズ共通処理 ---
def run_quiz(questions, mode_name):
    st.header(mode_name)

    if "quiz_mode" not in st.session_state or st.session_state.quiz_mode != mode_name:
        st.session_state.quiz_mode = mode_name
        st.session_state.quiz_index = 0
        st.session_state.correct = 0
        st.session_state.feedback = None

        random.shuffle(questions)
        st.session_state.questions = [
            {
                "data": q,
                "mode": random.choice(["EN_TO_JA", "JA_TO_EN"])
            }
            for q in questions
        ]

    idx = st.session_state.quiz_index
    questions = st.session_state.questions

    if idx >= len(questions):
        total = len(questions)
        percent = round(st.session_state.correct / total * 100, 1)
        st.success(f"🎉 終了！ {st.session_state.correct}/{total}（{percent}%）")
        save_result(mode_name, st.session_state.correct, total)

        if st.button("リセット"):
            for k in ["quiz_mode", "quiz_index", "correct", "questions", "feedback"]:
                st.session_state.pop(k, None)
            st.rerun()
        st.stop()

    item = questions[idx]
    word, meaning = item["data"][1], item["data"][2]

    if item["mode"] == "EN_TO_JA":
        question = f"「{word}」の意味は？"
        answer = meaning
    else:
        question = f"「{meaning}」の英単語は？"
        answer = word

    st.subheader(f"第 {idx+1} 問 / 全 {len(questions)} 問")
    st.write(question)

    user_ans = st.text_input("回答", key=f"ans_{idx}")

    # --- 回答ボタン ---
    if st.button("回答"):
        if user_ans.strip().lower() == answer.lower():
            st.session_state.feedback = ("correct", "✅ 正解！")
            st.session_state.correct += 1
        else:
            st.session_state.feedback = (
                "wrong",
                f"❌ 不正解。正解は「{answer}」"
            )

    # --- 結果表示 ---
    if st.session_state.feedback:
        kind, msg = st.session_state.feedback
        if kind == "correct":
            st.success(msg)
        else:
            st.error(msg)

        if st.button("次へ"):
            st.session_state.quiz_index += 1
            st.session_state.feedback = None
            st.rerun()

# --- メニュー処理 ---
if menu == "単語を追加":
    st.header("単語を追加")
    w = st.text_input("英単語")
    m = st.text_input("意味")
    if st.button("追加"):
        if w and m:
            add_word(w, m)
            st.success("追加しました")

elif menu == "CSV取り込み":
    st.header("CSV取り込み")
    file = st.file_uploader("CSV選択", type="csv")
    if file and st.button("取り込み"):
        count = import_words_from_csv(file)
        st.success(f"{count} 件追加")

elif menu == "単語一覧・削除":
    for w in get_all_words():
        col1, col2, col3 = st.columns([3,4,1])
        col1.write(w[1])
        col2.write(w[2])
        if col3.button("削除", key=w[0]):
            delete_word(w[0])
            st.rerun()

elif menu == "1問クイズ":
    words = get_all_words()
    if words:
        run_quiz(words[:1], "1問クイズ")
    else:
        st.info("単語がありません")

elif menu == "5問クイズ":
    words = get_all_words()
    if len(words) >= 5:
        run_quiz(words[:5], "5問クイズ")
    else:
        st.info("5語以上必要です")

elif menu == "全単語クイズ":
    words = get_all_words()
    if words:
        run_quiz(words, "全単語クイズ")
    else:
        st.info("単語がありません")

elif menu == "実績を見る":
    for r in get_results():
        st.write(f"{r[4]} | {r[0]} | {r[1]}/{r[2]} ({r[3]}%)")

# --- ヘルプ ---
elif menu == "ヘルプ":
    st.header("❓ ヘルプ・使い方")

    st.markdown("""
## 🧠 このアプリでできること
- 英単語と意味の登録
- CSVファイルからの一括登録
- クイズ（1問・5問・全問）
- 正答率の履歴保存と確認

---

## 📝 単語の追加方法
### ▶ 手入力
1. 「単語を追加」を選択
2. 英単語と意味を入力(例:単語・apple,banana  意味・リンゴ,バナナ)  
3. 「追加」を押す

---

## 📂 CSV取り込み方法
UTF-8で保存 → 取り込み開始
(CSVの例:apple,リンゴ {改行} banana,バナナ)  メモ帳やEXCELを使いましょう

---

## 🎯 クイズの使い方
- 英語 → 日本語
- 日本語 → 英語  
は自動でランダム出題されます。

---

## 📊 実績について
- クイズ終了ごとに自動保存
- 最新30件表示
- 平均正答率は自動計算

---

## ⚠️ よくあるエラー
- 文字化け → UTF-8保存
- 5問ができない → 単語5件以上必要

""")

#popcorn
