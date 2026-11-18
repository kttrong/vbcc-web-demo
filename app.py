
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Tra cứu VBCC - Demo",
    page_icon="🎓",
    layout="wide"
)

st.title("TRA CỨU VĂN BẰNG, CHỨNG CHỈ")
st.caption("Bản thử nghiệm - Dữ liệu giả lập")


data = pd.DataFrame([
    {
        "Họ và tên": "Nguyễn Văn A",
        "Ngày sinh": "01/01/2005",
        "Số hiệu bằng": "DEMO001"
    },
    {
        "Họ và tên": "Trần Thị B",
        "Ngày sinh": "15/06/2005",
        "Số hiệu bằng": "DEMO002"
    },
    {
        "Họ và tên": "Lê Văn C",
        "Ngày sinh": "20/09/2004",
        "Số hiệu bằng": "DEMO003"
    },
    {
        "Họ và tên": "Phạm Thị D",
        "Ngày sinh": "12/12/2005",
        "Số hiệu bằng": "DEMO004"
    },
    {
        "Họ và tên": "Hoàng Văn E",
        "Ngày sinh": "05/03/2006",
        "Số hiệu bằng": "DEMO005"
    }
])


name = st.text_input("Họ và tên")
dob = st.text_input("Ngày sinh")

if name or dob:
    result = data.copy()

    if name:
        result = result[
            result["Họ và tên"].str.contains(
                name, case=False, regex=False
            )
        ]

    if dob:
        result = result[
            result["Ngày sinh"].str.contains(
                dob, regex=False
            )
        ]

    st.write(f"Tìm thấy {len(result)} kết quả")
    st.dataframe(
        result,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Nhập họ tên hoặc ngày sinh để tra cứu.")
