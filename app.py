import unicodedata

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tra cứu VBCC - Demo", page_icon="🎓", layout="wide")


def normalize(text):
    text = unicodedata.normalize("NFD", str(text).lower().strip().replace("đ", "d"))
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


# Dữ liệu hoàn toàn giả lập, không phải hồ sơ văn bằng thật.
ho = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Phan", "Võ", "Đặng", "Bùi", "Đỗ"]
dem = ["Văn", "Thị", "Minh", "Ngọc", "Quang", "Thanh", "Hữu", "Kim", "Đức", "Gia"]
ten = ["An", "Bình", "Chi", "Dũng", "Hà", "Hương", "Khánh", "Lan", "Minh", "Phúc"]
records = []
for i in range(100):
    records.append({
        "Họ và tên": f"{ho[i % 10]} {dem[(i // 10 + i) % 10]} {ten[(i * 3 + i // 10) % 10]}",
        "Ngày sinh": f"{i % 28 + 1:02d}/{(i // 3) % 12 + 1:02d}/{2003 + i % 5}",
        "Số hiệu bằng": f"DEMO{i + 1:03d}",
    })
data = pd.DataFrame(records)

st.title("TRA CỨU VĂN BẰNG, CHỨNG CHỈ")
st.caption("Bản thử nghiệm cá nhân · 100 hồ sơ giả lập · Không có giá trị xác minh văn bằng")
st.metric("Số bản ghi thử nghiệm", f"{len(data):,}")

col1, col2, col3 = st.columns(3)
with col1:
    name = st.text_input("Họ và tên", placeholder="Ví dụ: Nguyen Van")
with col2:
    dob = st.text_input("Ngày sinh", placeholder="Ví dụ: 01/01/2005")
with col3:
    diploma = st.text_input("Số hiệu bằng", placeholder="Ví dụ: DEMO001")

if name.strip() or dob.strip() or diploma.strip():
    result = data.copy()
    if name.strip():
        result = result[result["Họ và tên"].map(normalize).str.contains(normalize(name), regex=False)]
    if dob.strip():
        result = result[result["Ngày sinh"].str.contains(dob.strip(), regex=False)]
    if diploma.strip():
        result = result[result["Số hiệu bằng"].str.contains(diploma.strip(), case=False, regex=False)]
    st.write(f"Tìm thấy **{len(result)}** kết quả")
    st.dataframe(result, use_container_width=True, hide_index=True)
else:
    st.info("Nhập ít nhất một thông tin để tra cứu. Ví dụ: số hiệu bằng DEMO001.")

st.warning("Đây là dữ liệu mô phỏng để kiểm thử chức năng, không dùng để xác thực văn bằng, chứng chỉ.")
