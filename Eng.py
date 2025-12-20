import streamlit as st
import random
import os
import csv
import io

# =====================
# CSV 設定
# =====================
BASE_DIR = os.path.dirname(__file__)
WORDS_CSV = os.path.join(BASE_DIR, "words.csv")

def init_csv():
    if not os.path.exists(WORDS_CSV):
        with open(WORDS_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["word", "meaning"])

# =====================
# CSV 操作
# =====================
def add_word(word, meaning):
    with open(WORDS_CSV, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([word, meaning])

def get_all_words():
    words = []
    with open(WORDS_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            words.append((i, row["word"], row["meaning"]))
    return words

def delete_word(index):
    with open(WORDS_CSV, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    data = rows[1:]
    data.pop(index)

    with open(WORDS_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

def import_words_from_csv(file):
    text = file.getvalue().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))

    count = 0
    with open(WORDS_CSV, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        for row in reader:
            if len(row) >= 2:
                word = row[0].strip()
                meaning = row[1].strip()
                if word and meaning:
                    writer.writerow([word, meaning])
                    count += 1
    return count

# =====================
# クイズ共通処理
# =====================
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
    qs = st.session_state.questions

    if idx >= len(qs):
        total = len(qs)
        percent = round(st.session_state.correct / total * 100, 1)
        st.success(f"🎉 終了！ {st.session_state.correct}/{total}（{percent}%）")

        if st.button("最初から"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        st.stop()

    item = qs[idx]
    word, meaning = item["data"][1], item["data"][2]

    if item["mode"] == "EN_TO_JA":
        question = f"「{word}」の意味は？"
        answer = meaning
    else:
        question = f"「{meaning}」の英単語は？"
        answer = word

    st.subheader(f"第 {idx+1} 問 / 全 {len(qs)} 問")
    st.write(question)

    user_ans = st.text_input("回答", key=f"ans_{idx}")

    if st.button("回答"):
        if user_ans.strip().lower() == answer.lower():
            st.session_state.feedback = ("correct", "✅ 正解！")
            st.session_state.correct += 1
        else:
            st.session_state.feedback = ("wrong", f"❌ 不正解。正解は「{answer}」")

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

# =====================
# Streamlit UI
# =====================
st.set_page_config(page_title="英単語クイズ", page_icon="🧠")
st.title("🧠 英単語クイズアプリ")

init_csv()

menu = st.sidebar.radio("メニュー", [
    "単語を追加",
    "CSV取り込み",
    "単語一覧・削除",
    "1問クイズ",
    "5問クイズ",
    "全単語クイズ",
    "ヘルプ"
])

# =====================
# メニュー処理
# =====================
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
        st.success(f"{count} 件追加しました")

elif menu == "単語一覧・削除":
    st.header("単語一覧")
    for w in get_all_words():
        col1, col2, col3 = st.columns([3, 4, 1])
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

elif menu == "ヘルプ":
    st.header("❓ ヘルプ")
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
