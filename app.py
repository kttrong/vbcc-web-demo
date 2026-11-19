import streamlit as st
import pandas as pd
import unicodedata
from pathlib import Path

st.set_page_config(page_title="Tra cứu VBCC - Bản thử nghiệm", page_icon="🎓", layout="centered")
st.title("TRA CỨU VĂN BẰNG, CHỨNG CHỈ")
st.warning("BẢN THỬ NGHIỆM - DỮ LIỆU GIẢ LẬP, KHÔNG CÓ GIÁ TRỊ XÁC MINH VĂN BẰNG")

def normalize(v):
    s = unicodedata.normalize("NFD", str(v or "").casefold())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d").strip()

@st.cache_data
def load_data():
    path = Path(__file__).parent / "vbcc_demo.xlsx"
    return pd.read_excel(path, sheet_name="Data", header=1, dtype=str).fillna("")

try:
    df = load_data()
except Exception as e:
    st.error("Không đọc được dữ liệu mẫu. Kiểm tra file vbcc_demo.xlsx và sheet Data.")
    st.stop()

with st.form("lookup"):
    so_hieu = st.text_input("Số hiệu bằng (bắt buộc)", placeholder="Ví dụ: DEMO00001")
    ho_ten = st.text_input("Họ và tên (bắt buộc)", placeholder="Ví dụ: Nguyễn Văn A")
    ngay_sinh = st.text_input("Ngày sinh (bắt buộc)", placeholder="dd/mm/yyyy")
    submit = st.form_submit_button("Tra cứu", type="primary")

if submit:
    if not all([so_hieu.strip(), ho_ten.strip(), ngay_sinh.strip()]):
        st.warning("Vui lòng nhập đầy đủ ba thông tin để đối chiếu.")
    else:
        found = df[
            df["Số hiệu bằng"].map(normalize).eq(normalize(so_hieu)) &
            df["Họ, chữ đệm và tên"].map(normalize).eq(normalize(ho_ten)) &
            df["Ngày, tháng, năm sinh"].astype(str).str.strip().eq(ngay_sinh.strip())
        ]
        if found.empty:
            st.info("Không tìm thấy thông tin khớp với dữ liệu thử nghiệm.")
        else:
            st.success("Có thông tin trùng khớp trong bộ dữ liệu giả lập.")
            st.write("Loại văn bằng:", found.iloc[0]["Tên văn bằng"])
            st.write("Tình trạng:", found.iloc[0]["Tình trạng văn bằng"])
            st.caption("Không sử dụng kết quả này để xác minh văn bằng thật.")
