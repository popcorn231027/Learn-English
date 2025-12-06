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
    cur.execute("SELECT mode, correct, total, percent, played_at FROM results ORDER BY id DESC LIMIT 30")
    data = cur.fetchall()
    conn.close()
    return data

# --- CSV 取り込み ---
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

# --- Streamlit アプリ ---
st.set_page_config(page_title="英単語クイズアプリ", page_icon="🧠", layout="centered")
st.title("🧠 英単語クイズアプリ（Streamlit版）")

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

# --- 単語追加 ---
if menu == "単語を追加":
    st.header("単語を追加（複数対応）")
    words_text = st.text_input("英単語（カンマ区切り可）")
    meanings_text = st.text_input("意味（カンマ区切り可）")

    if st.button("追加"):
        if not words_text or not meanings_text:
            st.warning("⚠️ 英単語と意味を入力してください。")
        else:
            words = [w.strip() for w in words_text.split(",") if w.strip()]
            meanings = [m.strip() for m in meanings_text.split(",") if m.strip()]

            if len(words) != len(meanings):
                st.error("❌ 単語と意味の数が一致していません。")
            else:
                for w, m in zip(words, meanings):
                    add_word(w, m)
                st.success(f"✅ {len(words)}件の単語を追加しました！")

# --- CSV取り込み ---
elif menu == "CSV取り込み":
    st.header("CSVから単語を取り込む")

    st.markdown("""
📄 **CSVフォーマット（UTF-8）**
""")

    file = st.file_uploader("CSVファイルを選択", type=["csv"])

    if file is not None:
        if st.button("取り込み開始"):
            try:
                count = import_words_from_csv(file)
                st.success(f"✅ {count} 件の単語を取り込みました！")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {e}")

# --- 単語一覧・削除 ---
elif menu == "単語一覧・削除":
    st.header("登録単語一覧")

    words = get_all_words()
    if not words:
        st.info("登録された単語がありません。")
    else:
        for w in words:
            col1, col2, col3 = st.columns([3, 4, 1])
            with col1:
                st.text(w[1])
            with col2:
                st.text(w[2])
            with col3:
                if st.button("🗑️ 削除", key=f"del_{w[0]}"):
                    delete_word(w[0])
                    st.success(f"「{w[1]}」を削除しました。")
                    st.experimental_rerun()

# --- クイズ共通処理 ---
def run_quiz(questions, mode_name):
    st.header(mode_name)

    if "quiz_mode" not in st.session_state or st.session_state.quiz_mode != mode_name:
        st.session_state.quiz_mode = mode_name
        st.session_state.quiz_index = 0
        st.session_state.correct = 0
        random.shuffle(questions)
        st.session_state._questions = questions

    questions = st.session_state._questions
    idx = st.session_state.quiz_index

    if idx >= len(questions):
        total = len(questions)
        percent = round(st.session_state.correct / total * 100, 1) if total > 0 else 0.0
        st.success(f"🎉 終了！ {st.session_state.correct}/{total}（{percent}%）")
        save_result(mode_name, st.session_state.correct, total)

        if st.button("リセット"):
            for k in ["quiz_mode", "quiz_index", "correct", "_questions"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.experimental_rerun()
        st.stop()

    q = questions[idx]
    mode = random.choice(["EN_TO_JA", "JA_TO_EN"])

    if mode == "EN_TO_JA":
        question_text = f"「{q[1]}」の意味は？"
        answer = q[2]
    else:
        question_text = f"「{q[2]}」の英単語は？"
        answer = q[1]

    st.subheader(f"第 {idx + 1} 問 / 全 {len(questions)}問")
    st.write(question_text)
    ans = st.text_input("回答を入力", key=f"ans_{idx}")

    if st.button("回答", key=f"btn_{idx}"):
        if ans.strip().lower() == str(answer).strip().lower():
            st.session_state.correct += 1
            st.success("✅ 正解！")
        else:
            st.error(f"❌ 不正解。正解は「{answer}」でした。")

        st.session_state.quiz_index += 1
        st.experimental_rerun()

# --- クイズ各モード ---
if menu == "1問クイズ":
    words = get_all_words()
    if not words:
        st.warning("単語が登録されていません。")
    else:
        run_quiz(random.sample(words, 1), "1問クイズ")

elif menu == "5問クイズ":
    words = get_all_words()
    if len(words) < 5:
        st.warning("5問以上の単語を登録してください。")
    else:
        run_quiz(random.sample(words, 5), "5問クイズ")

elif menu == "全単語クイズ":
    words = get_all_words()
    if not words:
        st.warning("単語が登録されていません。")
    else:
        run_quiz(words, "全単語クイズ")

# --- 実績表示 ---
elif menu == "実績を見る":
    st.header("クイズ実績")
    results = get_results()

    if not results:
        st.info("実績がまだありません。")
    else:
        for r in results:
            st.write(f"[{r[4]}] {r[0]}: {r[1]}/{r[2]} ({r[3]}%)")

        avg = sum(r[3] for r in results) / len(results)
        st.markdown(f"**平均正答率:** {avg:.1f}%")

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
