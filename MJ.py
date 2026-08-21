import streamlit as st
import pandas as pd
import os
import base64
import io
import re
from streamlit_gsheets import GSheetsConnection

# ================= 1. CẤU HÌNH TRANG =================
st.set_page_config(page_title="FREEBIE MJ FROM ĐẬU", page_icon="📦", layout="centered")

ADMIN_PASSWORD = "1708"
SHEET_ID = "1IB7wWROgUWjpRVRe_k1b16S3SqKoXvOvZYOemx73phE"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?usp=sharing"
LOCK_FILE = "lock_form.txt"

def is_form_locked(): return os.path.exists(LOCK_FILE)
def set_form_lock(locked):
    if locked:
        with open(LOCK_FILE, "w") as f: f.write("locked")
    else:
        if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)

# ================= 2. CÁC HÀM XỬ LÝ DỮ LIỆU TỪ CODE GỐC =================
def clean_phone(x):
    s = str(x).replace('.0', '').replace("'", "").strip()
    if s.lower() in ['nan', 'none', '']: return ""
    s_clean = s.replace(" ", "").replace(".", "")
    if s_clean.isdigit() and not s.startswith('0'): 
        return '0' + s_clean
    return s_clean

# Hàm Tẩy trần dữ liệu thần thánh - Bảo vệ toàn vẹn số 0 và chống lỗi Type
def clean_df_for_gsheets(df):
    cols_to_ensure = ['Checked SDT', 'Checked Địa chỉ', 'Checked Thành phố', 'Checked Phường xã', 'Địa chỉ đặc biệt', 'Trạng thái xác nhận', 'Lưu ý']
    for c in cols_to_ensure:
        if c not in df.columns: df[c] = ""
        df[c] = df[c].astype(object)
        
    def restore_phone_zero(x):
        s = str(x).replace('.0', '').replace("'", "").strip()
        if s.lower() in ['nan', 'none', '']: return ""
        s_clean = s.replace(" ", "").replace(".", "")
        if s_clean.isdigit() and not s.startswith('0'): 
            s = '0' + s_clean
        return s 
        
    for col in df.columns:
        col_upper = col.upper()
        if 'SDT' in col_upper or 'ĐIỆN THOẠI' in col_upper:
            df[col] = df[col].apply(restore_phone_zero)
            
    return df

# Hàm quét tỉnh/phường thông minh
def extract_location(address, loc_list):
    if pd.isna(address) or str(address).strip() == "": return ""
    addr_lower = str(address).lower()
    sorted_locs = sorted(loc_list, key=len, reverse=True)
    
    for loc in sorted_locs:
        clean_loc = loc.lower().replace("tỉnh ", "").replace("thành phố ", "").replace("phường ", "").replace("xã ", "").replace("đặc khu ", "")
        if clean_loc in addr_lower:
            return loc
    return ""

# ================= 3. HÀM TẢI DỮ LIỆU & CACHE =================
@st.cache_data(ttl=60)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_app = conn.read(spreadsheet=SHEET_URL, worksheet="Data App")
    df_resp = conn.read(spreadsheet=SHEET_URL, worksheet="Response")
    
    # Gom nhóm Tỉnh/Phường từ tab Ward
    try:
        df_ward = conn.read(spreadsheet=SHEET_URL, worksheet="Ward")
        df_ward.columns = df_ward.columns.str.strip()
        df_ward_clean = df_ward[['Thành phố', 'Phường xã']].dropna()
        # Tạo Dictionary {City: [Ward1, Ward2,...]}
        dict_city_ward = df_ward_clean.groupby('Thành phố')['Phường xã'].apply(lambda x: sorted([str(i).strip() for i in x if str(i).strip() != ''])).to_dict()
        list_city = sorted(list(dict_city_ward.keys()))
    except:
        list_city = []
        dict_city_ward = {}
    
    df_app.columns = df_app.columns.str.strip()
    df_resp.columns = df_resp.columns.str.strip()
    
    if 'SDT' in df_app.columns:
        df_app['SDT'] = df_app['SDT'].apply(clean_phone)
        
    return df_app, df_resp, list_city, dict_city_ward

try:
    df_app, df_resp, LIST_CITY, DICT_CITY_WARD = load_data()
except Exception as e:
    st.error("Đang có lỗi kết nối Google Sheet. Vui lòng thử lại sau!")
    st.stop()

# ================= 4. GIAO DIỆN & CSS =================
def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

img_title = get_image_base64("Web cover.jpg")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #333333; }
    h1, h2, h3, h4 { color: #0B192C !important; font-weight: bold; }
    button[kind="primary"] { background-color: #F4C430 !important; color: #0B192C !important; font-weight: bold !important; border: none; width: 100%; border-radius: 8px;}
    button[kind="primary"]:hover { background-color: #0B192C !important; color: #FFFFFF !important; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div { background-color: #F8F9FA; border: 1px solid #0B192C; border-radius: 5px; }
    .section-title { background: linear-gradient(90deg, #0B192C 0%, #F4C430 100%); color: white; padding: 12px 15px; border-radius: 8px 8px 0 0; font-size: 16px; font-weight: bold; margin-top: 25px; text-transform: uppercase; }
    .info-box { background-color: #FAFAFA; border: 1px solid #E0E6ED; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

if img_title:
    st.markdown(f"<div style='text-align: center; margin-bottom: 20px;'><img src='data:image/jpeg;base64,{img_title}' style='width: 100%; max-width: 800px; border-radius: 10px;'></div>", unsafe_allow_html=True)
else:
    st.markdown("<h1 style='text-align: center;'>📦 FREEBIE MJ FROM ĐẬU</h1>", unsafe_allow_html=True)

col_rf1, col_rf2 = st.columns([1, 3])
with col_rf1:
    if st.button("🔄 Cập nhật dữ liệu"):
        st.cache_data.clear()
        st.rerun()

tab1, tab2 = st.tabs(["🔍 KIỂM TRA THÔNG TIN", "🔒 ADMIN"])

# ================= TAB 1: KHÁCH HÀNG CHECK THÔNG TIN =================
with tab1:
    phone_input = st.text_input("Nhập số điện thoại của bạn:", placeholder="Ví dụ: 0901234567")
    
    if st.button("KIỂM TRA 🚀", type="primary"):
        if phone_input:
            clean_input = clean_phone(phone_input).lstrip('0')
            df_app['Phone_Compare'] = df_app['SDT'].astype(str).str.lstrip('0')
            user_orders = df_app[df_app['Phone_Compare'] == clean_input]
            
            if not user_orders.empty:
                st.session_state['verified_phone'] = clean_input 
                st.rerun()
            else:
                st.warning("Không tìm thấy đơn hàng nào với SĐT này. Bạn kiểm tra lại nhé!")
        else:
            st.warning("Bạn chưa nhập số điện thoại kìa!")

    if 'verified_phone' in st.session_state:
        clean_input = st.session_state['verified_phone']
        df_app['Phone_Compare'] = df_app['SDT'].astype(str).str.lstrip('0')
        user_orders = df_app[df_app['Phone_Compare'] == clean_input]
        row_data = user_orders.iloc[0]
        
        ten_kh = str(row_data.get('Tên', 'BẠN')).strip()
        original_phone = clean_phone(row_data.get('SDT', ''))
        original_address = str(row_data.get('Địa chỉ', '')).strip()
        ghi_chu_goc = str(row_data.get('Ghi chú', '')).strip()
        mvd = str(row_data.get('Mã vận đơn', '')).replace('nan', '').strip()
        
        chk_sdt = clean_phone(row_data.get('Checked SDT', ''))
        chk_dc = str(row_data.get('Checked Địa chỉ', '')).strip().replace("nan", "")
        chk_city = str(row_data.get('Checked Thành phố', '')).strip().replace("nan", "")
        chk_ward = str(row_data.get('Checked Phường xã', '')).strip().replace("nan", "")
        chk_special = str(row_data.get('Địa chỉ đặc biệt', '')).strip().replace("nan", "")
        tt_xacnhan = str(row_data.get('Trạng thái xác nhận', '')).strip()
        luu_y_cu = str(row_data.get('Lưu ý', '')).strip().replace("nan", "")

        is_locked = is_form_locked()
        
        # LOGIC XÁC NHẬN CHUẨN XÁC TỪ CODE CŨ (Phân biệt Xác nhận vs Cập nhật)
        has_update = False
        if (chk_sdt != "") and (chk_sdt != original_phone): has_update = True
        if (chk_dc != "") and (chk_dc != original_address): has_update = True
        if (chk_city != ""): has_update = True

        if tt_xacnhan == "Đã xác nhận":
            if chk_sdt: original_phone = chk_sdt
            if chk_dc: original_address = chk_dc
            
            if has_update:
                st.success(f"🎉 Chào {ten_kh.upper()} ơi, bạn đã cập nhật thông tin thành công rồi nha, dưới đây là kết quả cuối cùng của bạn!")
            else:
                st.success(f"🎉 Chào {ten_kh.upper()} ơi, bạn đã xác nhận thông tin thành công rồi nha, dưới đây là kết quả cuối cùng của bạn!")
        else:
            st.info(f"👋 Chào {ten_kh.upper()} ơi, bạn kiểm tra lại thông tin đơn hàng của mình nha!")

        # 1. THÔNG TIN VẬN CHUYỂN
        st.markdown("<div class='section-title'>🚚 THÔNG TIN VẬN CHUYỂN</div>", unsafe_allow_html=True)
        html_ship = "<div class='info-box'>"
        html_ship += "<div style='margin-bottom: 8px;'><b>Đơn vị vận chuyển:</b> <span style='color: #0B192C;'>SPX Express</span></div>"
        
        if mvd:
            html_ship += f"<div style='margin-bottom: 8px;'><b>Mã vận đơn:</b> <span style='color: #E74C3C; font-weight: bold; font-size: 16px;'>{mvd}</span></div>"
            html_ship += "<div style='margin-bottom: 8px;'><b>Link tra cứu:</b> <a href='https://spx.vn/vi' target='_blank' style='color: #0066CC;'>Bấm vào đây để tra cứu hành trình nha 🚀</a></div>"
        else:
            html_ship += "<div style='margin-bottom: 8px; color: #555; font-style: italic;'>Tụi mình sẽ cập nhật Mã vận đơn ngay sau khi book đơn nha ❤️</div>"
            
        if ghi_chu_goc and ghi_chu_goc.lower() != 'nan':
            html_ship += f"<hr style='border: 0.5px dashed #ccc; margin: 10px 0;'><div style='margin-bottom: 8px;'><b>Ghi chú đơn hàng:</b> {ghi_chu_goc}</div>"
            
        html_ship += "</div>"
        st.markdown(html_ship, unsafe_allow_html=True)

        # 2. THÔNG TIN GIAO HÀNG (Kèm Auto-fill)
        if is_locked:
            st.error("🔒 ĐÃ HẾT THỜI GIAN CẬP NHẬT. Thông tin bên dưới đã được chốt sổ.")

        st.markdown("<div class='section-title'>📍 THÔNG TIN GIAO HÀNG</div>", unsafe_allow_html=True)

        # Tính toán Auto-fill
        auto_city = chk_city if chk_city else extract_location(original_address, LIST_CITY)
        
        list_ward_options = DICT_CITY_WARD.get(auto_city, []) if auto_city else []
        auto_ward = chk_ward if chk_ward else extract_location(original_address, list_ward_options)

        if not is_locked:
            # Checkbox Đảo lên trên
            is_correct = st.checkbox("Thông tin giao hàng bên dưới đã chính xác.", value=True, key=f"chk_correct_{clean_input}")
            st.markdown("<div style='font-size: 13px; font-style: italic; color: #555; margin-top: -10px; margin-bottom: 15px;'>*Trong trường hợp bạn muốn cập nhật, bạn bỏ dấu tick phía đầu nha, và bạn đọc kỹ phần lưu ý về địa chỉ phía dưới giúp mình nha.</div>", unsafe_allow_html=True)

            # CARD CẢNH BÁO NỔI BẬT NẰM DƯỚI TEXT IN NGHIÊNG
            st.markdown("""
            <div style='border: 2px solid #E74C3C; border-radius: 8px; padding: 15px; background-color: #FDEDEC; margin-bottom: 20px;'>
                <b style='color: #C0392B; font-size: 15px;'>🚨 LƯU Ý ĐỊNH DẠNG ĐỊA CHỈ HỢP LỆ:</b><br>
                <ol style='color: #C0392B; margin-top: 5px; margin-bottom: 5px; padding-left: 20px;'>
                    <li>Chỉ bao gồm Số nhà, Đường, Phường/ Xã, Tỉnh/ Thành phố (Vd: 7A Thoại Ngọc Hầu, Phường Tân Phú, Tp.HCM).</li>
                    <li>Mọi lưu ý khác bạn điền ở phần Địa chỉ đặc biệt giúp mình nhé (bỏ tick đỏ phía trên sẽ thấy phần này nha).</li>
                    <li>Mọi người nhớ check kỹ phần Khu vực hành chính nha.</li>
                </ol>
                <i style='color: #C0392B;'>Vì để đảm bảo ship hàng không bị thất lạc do sự sáp nhập, mọi người chịu khó giúp mình nha.</i>
            </div>
            """, unsafe_allow_html=True)
            
            if not is_correct:
                st.markdown("<div style='color: #E74C3C; font-size: 14px; font-weight: bold;'>⚠️ CHỈ ĐIỀN VÀO Ô NÀO CẦN CẬP NHẬT. Giữ nguyên thì BỎ TRỐNG nhé!</div>", unsafe_allow_html=True)
                new_phone = st.text_input("SĐT Cập Nhật:", placeholder=f"Hiện tại: {original_phone}")
                new_address = st.text_area("Địa chỉ cập nhật (Số nhà, Đường, Phường/ Xã, Tỉnh/ Thành phố) - Vd: 7A Thoại Ngọc Hầu, Phường Tân Phú, Tp.HCM", placeholder=f"Hiện tại: {original_address}")
                
                st.markdown("<div style='font-weight: bold; color: #0B192C; margin-top: 10px;'>Khu vực hành chính sau sáp nhập của nhà bạn:</div>", unsafe_allow_html=True)
                
                # Chia 2 cột cho Dropdown
                col_c1, col_c2 = st.columns(2)
                
                # Cục Dropdown Thành phố
                city_options = ["-- Chọn Thành phố --"] + LIST_CITY
                default_city_idx = city_options.index(auto_city) if auto_city in city_options else 0
                selected_city = col_c1.selectbox("Thành phố", options=city_options, index=default_city_idx)
                
                # Cục Dropdown Phường xã (Phụ thuộc Thành phố)
                ward_options = ["-- Chọn Phường/Xã --"]
                if selected_city != "-- Chọn Thành phố --":
                    ward_options += DICT_CITY_WARD.get(selected_city, [])
                default_ward_idx = ward_options.index(auto_ward) if auto_ward in ward_options else 0
                selected_ward = col_c2.selectbox("Phường/Xã", options=ward_options, index=default_ward_idx)
                
                st.markdown("<div style='font-size: 12.5px; font-style: italic; color: #E74C3C; margin-top: -10px; margin-bottom: 15px;'>*Nếu khu vực hành chính sau sáp nhập chưa đúng, bạn nhớ chọn lại nha.</div>", unsafe_allow_html=True)
                
                new_special = st.text_input("Địa chỉ đặc biệt:", value=chk_special, placeholder="Ví dụ: Tòa nhà Etown 2, Cổng trường Nguyễn Khuyến...")
                st.markdown("<div style='font-size: 12.5px; font-style: italic; color: #555; margin-top: -10px; margin-bottom: 15px;'>(Nếu bạn có địa chỉ đặc biệt hoặc lưu ý về địa chỉ, một dữ kiện để shipper dễ nhận ra mà bạn muốn lưu ý thì bạn note vào đây nha)</div>", unsafe_allow_html=True)

                # Gán dữ liệu cuối cùng khi đang mở form sửa
                final_phone = new_phone if new_phone.strip() else original_phone
                final_address = new_address if new_address.strip() else original_address
                final_city = selected_city if selected_city != "-- Chọn Thành phố --" else ""
                final_ward = selected_ward if selected_ward != "-- Chọn Phường/Xã --" else ""
                final_special = new_special
            else:
                # Nếu tick đã chính xác, hiển thị dữ liệu gốc + auto-fill
                final_phone = original_phone
                final_address = original_address
                final_city = auto_city
                final_ward = auto_ward
                final_special = chk_special
        else:
            final_phone = original_phone
            final_address = original_address
            final_city = chk_city
            final_ward = chk_ward
            final_special = chk_special

        # Hiển thị Info Box chốt cuối
        html_info = f"<div class='info-box'>"
        html_info += f"<b>SĐT:</b> {final_phone}<br>"
        html_info += f"<b>Địa chỉ:</b> {final_address}<br>"
        html_info += f"<b>KHU VỰC HÀNH CHÍNH SAU SÁP NHẬP:</b><br>"
        html_info += f"<b>Tỉnh/Thành phố:</b> {final_city if final_city else '<span style=\"color:#E74C3C\">Chưa xác định</span>'}<br>"
        html_info += f"<b>Phường/Xã:</b> {final_ward if final_ward else '<span style=\"color:#E74C3C\">Chưa xác định</span>'}"
        if final_special: html_info += f"<br><b>Địa chỉ đặc biệt:</b> {final_special}"
        html_info += "</div>"
        st.markdown(html_info, unsafe_allow_html=True)

        # 3. LƯU Ý THÊM
        st.markdown("<div class='section-title'>📝 LƯU Ý THÊM</div>", unsafe_allow_html=True)
        if not is_locked:
            final_note = st.text_area("Bạn có muốn nhắn nhủ gì cho tụi mình không?", value=luu_y_cu)
        else:
            st.write(luu_y_cu)

        # 4. NÚT XÁC NHẬN (GHI ĐÈ LÊN TAB RESPONSE)
        if not is_locked:
            if st.button("🚀 XÁC NHẬN / CẬP NHẬT", type="primary"):
                # --- LOGIC CHẶN SIÊU CHẶT CHẼ ---
                no_changes = False
                if not is_correct:
                    # Nếu 3 ô text không điền gì
                    if new_phone.strip() == "" and new_address.strip() == "" and new_special.strip() == "":
                        # VÀ 2 cục dropdown vẫn y xì đúc như auto-fill ban đầu (chưa đổi)
                        if final_city == (auto_city if auto_city else "") and final_ward == (auto_ward if auto_ward else ""):
                            no_changes = True

                # CHẶN 1: Bỏ tick nhưng chả thay đổi thông tin gì
                if not is_correct and no_changes:
                    st.warning("⚠️ Bạn đã bỏ tick xác nhận, nhưng không nhập thông tin gì mới. Nếu mọi thứ đã đúng, bạn cứ tick lại giùm mình nha!")
                
                # CHẶN 2: Bỏ tick, có nhập thông tin nhưng QUÊN chọn Thành phố hoặc Phường/Xã
                elif not is_correct and (final_city == "" or final_ward == ""):
                    st.warning("⚠️ Bạn vui lòng chọn đầy đủ Thành phố và Phường/Xã nhé!")
                    
                # NẾU VƯỢT QUA HẾT CÁC ẢI CHẶN -> CHO LƯU DỮ LIỆU
                else:
                    with st.spinner("Đang lưu thông tin vào hệ thống..."):
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        df_target = conn.read(spreadsheet=SHEET_URL, worksheet="Response")
                        df_target.columns = df_target.columns.str.strip()
                        
                        # --- ĐOẠN CODE BẢO VỆ ÉP KIỂU (CHỐNG LỖI TYPE ERROR) ---
                        cols_to_update = ['SDT', 'Checked SDT', 'Checked Địa chỉ', 'Checked Thành phố', 'Checked Phường xã', 'Địa chỉ đặc biệt', 'Trạng thái xác nhận', 'Lưu ý']
                        for col in cols_to_update:
                            if col not in df_target.columns:
                                df_target[col] = ""
                            df_target[col] = df_target[col].astype(object)
                        # --------------------------------------------------------
                        
                        df_target['SDT_Compare'] = df_target['SDT'].apply(clean_phone).str.lstrip('0')
                        idx_list = df_target[df_target['SDT_Compare'] == clean_input].index
                        
                        if len(idx_list) > 0:
                            for idx in idx_list:
                                df_target.at[idx, 'Checked SDT'] = final_phone.strip()
                                df_target.at[idx, 'Checked Địa chỉ'] = final_address.strip()
                                df_target.at[idx, 'Checked Thành phố'] = final_city.strip()
                                df_target.at[idx, 'Checked Phường xã'] = final_ward.strip()
                                df_target.at[idx, 'Địa chỉ đặc biệt'] = final_special.strip()
                                df_target.at[idx, 'Trạng thái xác nhận'] = "Đã xác nhận"
                                df_target.at[idx, 'Lưu ý'] = final_note.strip()
                                
                            df_target = df_target.drop(columns=['SDT_Compare'])
                            
                            # TẨY TRẦN DỮ LIỆU ĐỂ BẢO ĐẢM KHÔNG BỊ MẤT SỐ 0
                            df_target = clean_df_for_gsheets(df_target)
                            
                            conn.update(spreadsheet=SHEET_URL, worksheet="Response", data=df_target)
                            st.cache_data.clear() 
                            st.success("✅ ĐÃ GHI NHẬN THÔNG TIN LÊN HỆ THỐNG! Cảm ơn bạn rất nhiều 💖")
                            st.balloons()
                        else:
                            st.error("Không tìm thấy dòng tương ứng trong tab Response để ghi đè. Báo Admin nhé!")

# ================= TAB 2: ADMIN =================
with tab2:
    pass_admin = st.text_input("Nhập mật khẩu Admin:", type="password")
    
    if pass_admin == ADMIN_PASSWORD:
        st.success("Đăng nhập thành công!")
        
        is_locked = is_form_locked()
        toggle_lock = st.toggle("🔒 KHÓA CẬP NHẬT (Fan không thể sửa form nữa)", value=is_locked)
        if toggle_lock != is_locked:
            set_form_lock(toggle_lock)
            st.rerun()
        st.divider()

        # --- TIẾN ĐỘ XÁC NHẬN ---
        st.markdown("#### 📦 TIẾN ĐỘ XÁC NHẬN")
        total_orders = len(df_app)
        
        df_confirmed = df_app[df_app['Trạng thái xác nhận'].astype(str).str.strip() == 'Đã xác nhận']
        confirmed_total = len(df_confirmed)
        
        # Hàm HAS_UPDATE với safe_str siêu việt từ code cũ
        def has_update(row):
            def safe_str(val):
                if pd.isna(val): return ""
                s = str(val).strip()
                if s.lower() in ['nan', 'none', '<na>', 'nat', '']: return ""
                return s
                
            orig_sdt = safe_str(row.get('SDT', '')).replace('.0', '').replace("'", "")
            if orig_sdt.isdigit() and not orig_sdt.startswith('0'): orig_sdt = '0' + orig_sdt
            orig_dc = safe_str(row.get('Địa chỉ', ''))
            
            chk_sdt = safe_str(row.get('Checked SDT', '')).replace('.0', '').replace("'", "")
            if chk_sdt.isdigit() and not chk_sdt.startswith('0'): chk_sdt = '0' + chk_sdt
            chk_dc = safe_str(row.get('Checked Địa chỉ', ''))
            chk_city = safe_str(row.get('Checked Thành phố', ''))

            if chk_sdt != '' and chk_sdt != orig_sdt: return True
            if chk_dc != '' and chk_dc != orig_dc: return True
            if chk_city != '': return True # Có xác nhận chọn Tỉnh/Thành
            return False

        updated_count = df_confirmed.apply(has_update, axis=1).sum() if confirmed_total > 0 else 0
        just_confirmed_count = confirmed_total - updated_count
        not_confirmed = total_orders - confirmed_total
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Tổng đơn", total_orders)
        c2.metric("👌 Chỉ Xác Nhận", just_confirmed_count)
        c3.metric("✍️ Có Cập Nhật", updated_count)
        c4.metric("⏳ Đang chờ", not_confirmed)
        st.divider()

        # --- TẠO DATA CHUẨN ĐỂ XUẤT FILE & HIỂN THỊ ---
        def get_final_row(row):
            def s_str(val): return str(val).replace('nan','').replace('None','').strip()
            
            f_phone = clean_phone(s_str(row.get('Checked SDT'))) or clean_phone(s_str(row.get('SDT')))
            f_add = s_str(row.get('Checked Địa chỉ')) or s_str(row.get('Địa chỉ'))
            
            # Cứu net Tỉnh/Phường: Nếu khách quên chưa tick xác nhận, tự động đoán cho Admin xuất file
            f_city = s_str(row.get('Checked Thành phố'))
            if not f_city: f_city = extract_location(f_add, LIST_CITY)
            
            f_ward = s_str(row.get('Checked Phường xã'))
            if not f_ward and f_city: f_ward = extract_location(f_add, DICT_CITY_WARD.get(f_city, []))
            
            f_spec = s_str(row.get('Địa chỉ đặc biệt'))
            return pd.Series([f_phone, f_add, f_city, f_ward, f_spec])

        df_export_base = df_confirmed.copy()
        
        # Thêm cột cờ đánh dấu cập nhật để phân loại danh sách hiển thị
        if not df_export_base.empty:
            df_export_base['Is_Updated'] = df_export_base.apply(has_update, axis=1)
            df_export_base[['Final_Phone', 'Final_Address', 'Final_City', 'Final_Ward', 'Final_Special']] = df_export_base.apply(get_final_row, axis=1)
        
        # --- HIỂN THỊ CHI TIẾT DANH SÁCH ---
        st.markdown("#### 📋 CHI TIẾT DANH SÁCH ĐÃ XÁC NHẬN")
        col_list1, col_list2 = st.columns(2)
        
        with col_list1:
            with st.expander(f"📝 Danh sách CÓ CẬP NHẬT ({updated_count})"):
                if not df_export_base.empty:
                    df_upd = df_export_base[df_export_base['Is_Updated'] == True]
                    if not df_upd.empty:
                        for _, r in df_upd.iterrows():
                            t = str(r.get('Tên', '')).replace('nan','').strip()
                            p = str(r.get('Final_Phone', '')).replace('nan','').strip()
                            a = str(r.get('Final_Address', '')).replace('nan','').strip()
                            w = str(r.get('Final_Ward', '')).replace('nan','').strip()
                            c = str(r.get('Final_City', '')).replace('nan','').strip()
                            st.markdown(f"- **{t}** | 📞 {p}<br>🏠 <span style='font-size:13px; color:#555;'>{a}, {w}, {c}</span>", unsafe_allow_html=True)
                    else:
                        st.info("Chưa có ai.")
                else:
                    st.info("Chưa có ai.")
                    
        with col_list2:
            with st.expander(f"👌 Danh sách CHỈ XÁC NHẬN ({just_confirmed_count})"):
                if not df_export_base.empty:
                    df_just = df_export_base[df_export_base['Is_Updated'] == False]
                    if not df_just.empty:
                        for _, r in df_just.iterrows():
                            t = str(r.get('Tên', '')).replace('nan','').strip()
                            p = str(r.get('Final_Phone', '')).replace('nan','').strip()
                            a = str(r.get('Final_Address', '')).replace('nan','').strip()
                            w = str(r.get('Final_Ward', '')).replace('nan','').strip()
                            c = str(r.get('Final_City', '')).replace('nan','').strip()
                            st.markdown(f"- **{t}** | 📞 {p}<br>🏠 <span style='font-size:13px; color:#555;'>{a}, {w}, {c}</span>", unsafe_allow_html=True)
                    else:
                        st.info("Chưa có ai.")
                else:
                    st.info("Chưa có ai.")
                    
        st.divider()
        
        # --- DOWNLOAD FILE EXCEL (FORM SPX) ---
        st.markdown("### 📥 TẢI FILE EXCEL - FORM SPX")
        if st.button("Tạo File Excel SPX"):
            if df_export_base.empty:
                st.warning("Hiện chưa có ai xác nhận để tải file!")
            else:
                df_spx = pd.DataFrame()
                df_spx['*Tên người nhận'] = df_export_base['Tên']
                df_spx['*Số điện thoại'] = df_export_base['Final_Phone'].apply(lambda x: f"'{x}") 
                df_spx['*Tỉnh/Thành Phố'] = df_export_base['Final_City']
                df_spx['*Xã/Phường'] = df_export_base['Final_Ward']
                df_spx['*Địa chỉ chi tiết'] = df_export_base['Final_Address']
                df_spx['Lưu ý về địa chỉ'] = df_export_base['Final_Special']
                df_spx['Mã bưu chính'] = ""
                df_spx['*Tên sản phẩm'] = "Quà từ Đậu"
                df_spx['Số lượng'] = 1
                df_spx['Giá tiền'] = 0
                df_spx['*Tổng cân nặng bưu gửi (KG)'] = 0.5
                df_spx['Chiều dài (CM)'] = 30
                df_spx['Chiều rộng (CM)'] = 10
                df_spx['Chiều cao (CM)'] = 1
                df_spx['Mã khách hàng'] = ""
                df_spx['*Giá trị đơn hàng'] = 0
                df_spx['*Giao hàng một phần (Y/N)'] = "N"
                df_spx['*Cho phép thử hàng (Y/N)'] = "N"
                df_spx['*Cho xem hàng, không cho thử (Y/N)'] = "N"
                df_spx['Thu phí từ chối nhận hàng (Y/N)'] = "N"
                df_spx['Phí từ chối nhận hàng cần thu'] = ""
                df_spx['*Thu COD (Y/N)'] = "N"
                df_spx['Số tiền COD'] = ""
                df_spx['bưu gửi giá trị cao (Y/N)'] = "N"
                df_spx['*Hình thức thanh Toán'] = "Người nhận trả"

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_spx.to_excel(writer, index=False, sheet_name='Form SPX')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 TẢI FILE EXCEL SPX (.xlsx)",
                    data=excel_data,
                    file_name="Form_Tao_Don_SPX.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
        st.divider()

        # --- DOWNLOAD LABLE IN ĐƠN ---
        st.markdown("### 🖨️ TẢI FILE LABEL DÁN THÙNG")
        if st.button("Tạo File In Label HTML"):
            if df_export_base.empty:
                st.warning("Hiện chưa có ai xác nhận để tải Label!")
            else:
                html_content = """
                <html><head><meta charset="utf-8">
                <style>
                    @page { size: 100mm 150mm; margin: 0; }
                    body { font-family: Arial, sans-serif; margin: 0; padding: 3mm; background-color: #f4f4f9; }
                    .grid-container { display: flex; flex-direction: column; gap: 3mm; }
                    .label-box { width: 94mm; height: auto; min-height: 40mm; background: #fff; border: 2px dashed #000; padding: 10px; border-radius: 5px; box-sizing: border-box; page-break-inside: avoid; }
                    .title { font-size: 16px; font-weight: bold; color: #000; border-bottom: 2px solid #000; padding-bottom: 4px; margin-bottom: 6px; }
                    .info { font-size: 14px; margin-bottom: 4px; line-height: 1.4; color: #000; }
                    .note { font-size: 13px; font-style: italic; color: #555; margin-top: 6px; border-top: 1px dotted #ccc; padding-top: 4px; }
                </style></head><body><div class="grid-container">
                """
                
                for index, row in df_export_base.iterrows():
                    ten = str(row.get('Tên', '')).replace('nan', '').strip()
                    sdt = str(row.get('Final_Phone', '')).replace('nan', '').strip()
                    diachi = str(row.get('Final_Address', '')).replace('nan', '').strip()
                    tp = str(row.get('Final_City', '')).replace('nan', '').strip()
                    px = str(row.get('Final_Ward', '')).replace('nan', '').strip()
                    spec = str(row.get('Final_Special', '')).replace('nan', '').strip()
                    mvd = str(row.get('Mã vận đơn', '')).replace('nan', '').strip()
                    ghichu = str(row.get('Ghi chú', '')).replace('nan', '').strip()
                    
                    mvd_text = f"📦 MÃ VĐ: {mvd}" if mvd else "📦 MÃ VĐ: ......................"
                    full_address = f"{diachi}, {px}, {tp}".strip(", ")
                    
                    html_content += f"""
                    <div class="label-box">
                        <div class="title">{mvd_text}</div>
                        <div class="info">👤 <b>{ten}</b> <br>📞 {sdt}</div>
                        <div class="info">🏠 {full_address}</div>
                    """
                    if spec: html_content += f"<div class='info'>📍 Đặc biệt: <b>{spec}</b></div>"
                    if ghichu: html_content += f"<div class='note'>📝 Ghi chú: {ghichu}</div>"
                        
                    html_content += "</div>"
                    
                html_content += "</div></body></html>"
                
                st.success("Đã tạo Label thành công!")
                st.download_button(
                    label="📥 TẢI FILE IN LABLE (.html)", 
                    data=html_content, 
                    file_name="Label_SPX_Nhanh.html", 
                    mime="text/html"
                )

    elif pass_admin != "":
        st.error("Sai mật khẩu!")
