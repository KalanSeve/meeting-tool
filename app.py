import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import requests
import pandas as pd
import io

# ================= 页面基础设置 =================
st.set_page_config(page_title="智能会议助手", page_icon="📅", layout="wide")

# 注入全局 CSS 样式
st.markdown("""
<style>
    .main-title-container {
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 20px 30px;
        border-radius: 10px;
        margin-bottom: 25px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .main-title-container h1 {
        color: white !important;
        margin: 0;
        font-size: 2.2rem;
    }
</style>
""", unsafe_allow_html=True)

# 大标题（去掉了括号内容）
st.markdown("""
<div class="main-title-container">
    <h1>📅 智能会议助手</h1>
</div>
""", unsafe_allow_html=True)

# ================= 数据库初始化 =================
def init_db():
    conn = sqlite3.connect('meeting.db')
    c = conn.cursor()
    # 既然不要申请人了，数据库保留原有字段即可，不影响
    c.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  room TEXT, title TEXT, start_time TEXT, end_time TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ================= 侧边栏 =================
st.sidebar.header("功能导航")
menu = st.sidebar.radio("选择功能", ["1. 会议室申请", "2. 通知模板生成", "3. AI 纪要风格仿写", "4. 决议事项与任务提取"])

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ AI 引擎设置")
api_key = st.sidebar.text_input("DeepSeek API Key", type="password", help="填入你自己的 API Key，仅在当前会话有效。")

# ================= 功能一：会议室申请 =================
if menu == "1. 会议室申请":
    st.header("会议室申请与占用查看")
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("📝 申请会议室")
        room = st.selectbox("选择会议室", ["大会议室", "小会议室", "党建会议室", "会客厅"])
        title = st.text_input("会议名称")
        
        st.markdown("**选择时间**")
        date = st.date_input("日期", datetime.now(), label_visibility="collapsed")
        
        time_col1, time_col2 = st.columns(2)
        with time_col1:
            start_time = st.time_input("开始时间", datetime.now().replace(minute=0, second=0), label_visibility="collapsed")
        with time_col2:
            end_time = st.time_input("结束时间", (datetime.now() + timedelta(hours=1)).replace(minute=0, second=0), label_visibility="collapsed")
        
        st.write("")
        if st.button("提交申请", type="primary", use_container_width=True):
            if not title:
                st.warning("请填写会议名称！")
            else:
                start_str = f"{date} {start_time.strftime('%H:%M')}"
                end_str = f"{date} {end_time.strftime('%H:%M')}"
                conn = sqlite3.connect('meeting.db')
                c = conn.cursor()
                c.execute('''SELECT * FROM bookings WHERE room=? AND start_time<? AND end_time>?''', (room, end_str, start_str))
                conflict = c.fetchone()
                if conflict:
                    st.error("❌ 预约失败：该时段该会议室已被占用！")
                else:
                    c.execute("INSERT INTO bookings (room, title, start_time, end_time) VALUES (?, ?, ?, ?)", 
                              (room, title, start_str, end_str))
                    conn.commit()
                    st.success("✅ 预约成功！")
                conn.close()
                st.rerun()

    with col2:
        st.subheader("📅 全部会议预约情况")
        
        # 增加检索范围
        today = datetime.now().date()
        default_start = today - timedelta(days=today.weekday()) # 默认本周一
        default_end = default_start + timedelta(days=6)        # 默认本周日
        
        st.markdown("**检索范围**")
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            search_start = st.date_input("开始日期", default_start)
        with date_col2:
            search_end = st.date_input("结束日期", default_end)
            
        conn = sqlite3.connect('meeting.db')
        c = conn.cursor()
        c.execute("SELECT id, room, title, start_time, end_time FROM bookings WHERE date(start_time) >= ? AND date(start_time) <= ? ORDER BY start_time", (str(search_start), str(search_end)))
        rows = c.fetchall()
        conn.close()
        
        if rows:
            # 使用 st.data_editor 实现带删除按钮的表格
            df = pd.DataFrame(rows, columns=["ID", "会议室", "会议名称", "开始时间", "结束时间"])
            
            # 插入一列“取消预约”，用于复选框操作
            df.insert(0, "选择取消", False)
            
            st.caption("勾选第一列的复选框，然后点击下方按钮即可取消对应会议。")
            
            # 生成可编辑表格（隐藏 ID 列）
            edited_df = st.data_editor(
                df.drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "选择取消": st.column_config.CheckboxColumn(
                        "选择取消",
                        default=False,
                    )
                },
                disabled=["会议室", "会议名称", "开始时间", "结束时间"] # 锁定其他列不可修改
            )
            
            # 找到被勾选的行
            selected_rows = edited_df[edited_df["选择取消"] == True]
            
            if not selected_rows.empty:
                if st.button("🗑️ 取消选中的会议", type="secondary"):
                    conn = sqlite3.connect('meeting.db')
                    c = conn.cursor()
                    for index, row in selected_rows.iterrows():
                        # 通过匹配内容来寻找原本的 ID 进行删除
                        c.execute("DELETE FROM bookings WHERE start_time=? AND room=? AND title=?", 
                                  (row["开始时间"], row["会议室"], row["会议名称"]))
                    conn.commit()
                    conn.close()
                    st.success("✅ 已成功取消选中的会议！")
                    st.rerun()
        else:
            st.info(f"在 {search_start} 至 {search_end} 期间，暂无会议安排。")

# ================= 功能二：通知模板生成 =================
elif menu == "2. 通知模板生成":
    st.header("会议通知模板生成器")
    templates = {
        "正式通知": "【会议通知】\n主题：{title}\n时间：{time}\n地点：{room}\n参会人员：{people}\n会议要求：{req}\n请各位准时参加，收到请回复。",
        "简短通知": "📢 各位好，我们将于 {time} 在 {room} 召开关于【{title}】的会议。参会人：{people}。要求：{req}。请留意。"
    }
    template_choice = st.selectbox("选择通知模板", list(templates.keys()))
    col1, col2 = st.columns(2)
    with col1:
        t_title = st.text_input("会议主题")
        t_time = st.text_input("会议时间 (如：10月20日 下午2点)")
        t_room = st.text_input("会议地点")
    with col2:
        t_people = st.text_input("参会人员")
        t_req = st.text_input("会议要求 (如：携带图纸、准备汇报PPT)")
        
    if st.button("生成通知文本", type="primary"):
        result = templates[template_choice].format(title=t_title, time=t_time, room=t_room, people=t_people, req=t_req)
        st.text_area("👇 生成结果（可直接复制）", value=result, height=200)


# ================= 功能三：AI 纪要风格仿写 =================
elif menu == "3. AI 纪要风格仿写":
    st.header("AI 会议纪要风格仿写")
    st.markdown("输入**历史纪要**提供格式与语气参考，再输入**本次会议散乱要点**，AI 将为你生成结构一致、文风相符的纪要。")
    
    col1, col2 = st.columns(2)
    with col1:
        style_text = st.text_area("📚 历史纪要样例（风格与结构参考）", height=250, placeholder="粘贴一段以前的优秀纪要...")
    with col2:
        draft_text = st.text_area("📝 本次会议草稿/录音转写要点", height=250, placeholder="粘贴本次会议的零散记录...")
    
    if st.button("✨ 一键生成正式纪要", type="primary"):
        if not api_key: 
            st.warning("⚠️ 请先在左侧侧边栏填写你的 API Key。")
        elif not style_text or not draft_text: 
            st.warning("请填写完整。")
        else:
            with st.spinner("AI 正在深度分析结构并模仿风格..."):
                prompt = f"""你是一个资深的国企/工程企业办公室主任。请仔细阅读【样例纪要】，分析它的段落结构（例如是否有“一、会议基本情况”、“二、议定事项”）、用词习惯和行文语气。
然后，请将【本次草稿】改写成一份正式的会议纪要，必须严格模仿【样例纪要】的格式和文风。

【样例纪要】：
{style_text}

【本次草稿】：
{draft_text}

请直接输出纪要正文："""
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    data = {
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    }
                    response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data)
                    response.raise_for_status()
                    ai_result = response.json()['choices'][0]['message']['content']
                    
                    st.success("生成完成！")
                    st.text_area("👇 生成的会议纪要", value=ai_result, height=300)
                    st.session_state['latest_minutes'] = ai_result
                    st.info("💡 你可以复制上方文本，或者前往左侧【4. 决议事项与任务提取】自动生成待办表。")
                except Exception as e:
                    st.error(f"调用失败，请检查 Key 或网络。错误信息：{e}")


# ================= 功能四：决议事项提取 =================
elif menu == "4. 决议事项与任务提取":
    st.header("🎯 决议事项自动提取与任务跟踪")
    st.markdown("从会议纪要中自动识别**工作事项、责任人、完成时限**，生成标准待办清单。")
    
    default_text = st.session_state.get('latest_minutes', '')
    minutes_text = st.text_area("📄 会议纪要内容", value=default_text, height=200, placeholder="请粘贴会议纪要...")
    
    if st.button("🔍 自动提取任务清单", type="primary"):
        if not api_key: 
            st.warning("⚠️ 请先在左侧侧边栏填写你的 API Key。")
        elif not minutes_text: 
            st.warning("请提供纪要内容。")
        else:
            with st.spinner("AI 正在扮演项目经理，识别关键任务..."):
                prompt = f"""你是一个专业的项目管理助手。请阅读以下会议纪要，提取出所有的“工作事项/任务”。
请务必以纯 CSV 格式输出（第一行是表头），包含四列：任务事项, 责任人/部门, 完成时限, 具体要求。
如果纪要中没有明确责任人，请填“未指定”；没有明确时间，请填“待定”。
不要输出任何多余的解释，只输出 CSV 文本。

【会议纪要】：
{minutes_text}"""
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    data = {
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    }
                    response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data)
                    response.raise_for_status()
                    
                    csv_result = response.json()['choices'][0]['message']['content']
                    # 清理可能存在的 markdown 代码块符号
                    csv_result = csv_result.replace("```csv", "").replace("```", "").strip()
                    
                    df = pd.read_csv(io.StringIO(csv_result))
                    
                    st.success("提取成功！已生成任务跟踪表。")
                    st.dataframe(df, use_container_width=True)
                    
                    csv_data = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 下载任务清单 (CSV)",
                        data=csv_data,
                        file_name='会议任务清单.csv',
                        mime='text/csv',
                    )
                    st.info("💡 你可以下载此表并发给行政部门，或者导入到公司的项目管理软件中。")
                except Exception as e:
                    st.error(f"提取失败，AI可能没按格式输出，请重试。错误信息：{e}")import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import requests
import pandas as pd
import io

# ================= 页面基础设置 =================
st.set_page_config(page_title="智能会议助手", page_icon="📅", layout="wide")

# 注入全局 CSS 样式，实现区域颜色区分
st.markdown("""
<style>
    /* 大标题渐变背景 */
    .main-title-container {
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 20px 30px;
        border-radius: 10px;
        margin-bottom: 25px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .main-title-container h1 {
        color: white !important;
        margin: 0;
        font-size: 2.2rem;
    }
    /* 侧边栏样式微调 */
    .st-emotion-cache-1cypcdb {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# 生成你的总 Title 区域
st.markdown("""
<div class="main-title-container">
    <h1>📅 智能会议助手 (AI 办公流闭环)</h1>
</div>
""", unsafe_allow_html=True)

# ================= 数据库初始化 =================
def init_db():
    conn = sqlite3.connect('meeting.db')
    c = conn.cursor()
    # 增加了 creator 字段来记录申请人
    c.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  room TEXT, title TEXT, start_time TEXT, end_time TEXT, creator TEXT)''')
    conn.commit()
    conn.close()

# 兼容旧数据库：如果表已经存在但没 creator 字段，补充一下
def upgrade_db():
    conn = sqlite3.connect('meeting.db')
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE bookings ADD COLUMN creator TEXT")
    except sqlite3.OperationalError:
        pass # 字段已存在，忽略
    conn.commit()
    conn.close()

init_db()
upgrade_db()

# ================= 侧边栏 =================
st.sidebar.header("功能导航")
# 1. 名字修改为“会议室申请”
menu = st.sidebar.radio("选择功能", ["1. 会议室申请", "2. 通知模板生成", "3. AI 纪要风格仿写", "4. 决议事项与任务提取"])

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ AI 引擎设置")
# 将 API Key 提到侧边栏，全局可用，谁用谁填
api_key = st.sidebar.text_input("DeepSeek API Key", type="password", help="填入你自己的 API Key，仅在当前会话有效，不会保存。")

# ================= 功能一：会议室申请 =================
if menu == "1. 会议室申请":
    st.header("会议室申请与占用查看")
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("📝 申请会议室")
        # 增加申请人输入
        applicant = st.text_input("申请人姓名 (必填)")
        room = st.selectbox("选择会议室", ["大会议室", "小会议室", "党建会议室", "会客厅"])
        title = st.text_input("会议名称")
        
        st.markdown("**选择时间**")
        date = st.date_input("日期", datetime.now(), label_visibility="collapsed")
        
        time_col1, time_col2 = st.columns(2)
        with time_col1:
            start_time = st.time_input("开始时间", datetime.now().replace(minute=0, second=0), label_visibility="collapsed")
        with time_col2:
            end_time = st.time_input("结束时间", (datetime.now() + timedelta(hours=1)).replace(minute=0, second=0), label_visibility="collapsed")
        
        st.write("")
        if st.button("提交申请", type="primary", use_container_width=True):
            if not applicant:
                st.warning("请填写申请人姓名！")
            elif not title:
                st.warning("请填写会议名称！")
            else:
                start_str = f"{date} {start_time.strftime('%H:%M')}"
                end_str = f"{date} {end_time.strftime('%H:%M')}"
                conn = sqlite3.connect('meeting.db')
                c = conn.cursor()
                c.execute('''SELECT * FROM bookings WHERE room=? AND start_time<? AND end_time>?''', (room, end_str, start_str))
                conflict = c.fetchone()
                if conflict:
                    st.error("❌ 预约失败：该时段该会议室已被占用！")
                else:
                    c.execute("INSERT INTO bookings (room, title, start_time, end_time, creator) VALUES (?, ?, ?, ?, ?)", 
                              (room, title, start_str, end_str, applicant))
                    conn.commit()
                    st.success("✅ 预约成功！")
                conn.close()
                st.rerun()

    with col2:
        st.subheader("📅 本周会议室预约情况")
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        st.caption(f"当前展示范围：{start_of_week} 至 {end_of_week}")
        
        conn = sqlite3.connect('meeting.db')
        c = conn.cursor()
        c.execute("SELECT id, room, title, start_time, end_time, creator FROM bookings WHERE date(start_time) >= ? AND date(start_time) <= ? ORDER BY start_time", (str(start_of_week), str(end_of_week)))
        rows = c.fetchall()
        conn.close()
        
        if rows:
            # 展示时隐藏 ID 列
            df = pd.DataFrame(rows, columns=["ID", "会议室", "会议名称", "开始时间", "结束时间", "申请人"])
            st.dataframe(df.drop(columns=["ID"]), use_container_width=True, hide_index=True)
            
            # 新增：个人取消预约逻辑
            st.markdown("---")
            st.markdown("**🗑️ 取消我的预约**")
            cancel_user = st.text_input("请输入你的姓名以查找并取消你的会议：")
            if cancel_user:
                my_bookings = [r for r in rows if r[5] == cancel_user]
                if my_bookings:
                    for mb in my_bookings:
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.write(f"🔸 {mb[2]} | {mb[3]} - {mb[4]} ({mb[1]})")
                        with c2:
                            if st.button("取消预约", key=f"del_{mb[0]}"):
                                conn = sqlite3.connect('meeting.db')
                                c = conn.cursor()
                                c.execute("DELETE FROM bookings WHERE id = ?", (mb[0],))
                                conn.commit()
                                conn.close()
                                st.success("已取消该预约！")
                                st.rerun()
                else:
                    st.info("没有找到你名下的预约记录。")
        else:
            st.info("本周暂无会议安排，所有会议室均空闲。")

# ================= 功能二：通知模板生成 =================
elif menu == "2. 通知模板生成":
    st.header("会议通知模板生成器")
    templates = {
        "正式通知": "【会议通知】\n主题：{title}\n时间：{time}\n地点：{room}\n参会人员：{people}\n会议要求：{req}\n请各位准时参加，收到请回复。",
        "简短通知": "📢 各位好，我们将于 {time} 在 {room} 召开关于【{title}】的会议。参会人：{people}。要求：{req}。请留意。"
    }
    template_choice = st.selectbox("选择通知模板", list(templates.keys()))
    col1, col2 = st.columns(2)
    with col1:
        t_title = st.text_input("会议主题")
        t_time = st.text_input("会议时间 (如：10月20日 下午2点)")
        t_room = st.text_input("会议地点")
    with col2:
        t_people = st.text_input("参会人员")
        t_req = st.text_input("会议要求 (如：携带图纸、准备汇报PPT)")
        
    if st.button("生成通知文本", type="primary"):
        result = templates[template_choice].format(title=t_title, time=t_time, room=t_room, people=t_people, req=t_req)
        st.text_area("👇 生成结果（可直接复制）", value=result, height=200)


# ================= 功能三：AI 纪要风格仿写 =================
elif menu == "3. AI 纪要风格仿写":
    st.header("AI 会议纪要风格仿写")
    st.markdown("输入**历史纪要**提供格式与语气参考，再输入**本次会议散乱要点**，AI 将为你生成结构一致、文风相符的纪要。")
    
    col1, col2 = st.columns(2)
    with col1:
        style_text = st.text_area("📚 历史纪要样例（风格与结构参考）", height=250, placeholder="粘贴一段以前的优秀纪要...")
    with col2:
        draft_text = st.text_area("📝 本次会议草稿/录音转写要点", height=250, placeholder="粘贴本次会议的零散记录...")
    
    if st.button("✨ 一键生成正式纪要", type="primary"):
        if not api_key: 
            st.warning("⚠️ 请先在左侧侧边栏填写你的 API Key。")
        elif not style_text or not draft_text: 
            st.warning("请填写完整。")
        else:
            with st.spinner("AI 正在深度分析结构并模仿风格..."):
                prompt = f"""你是一个资深的国企/工程企业办公室主任。请仔细阅读【样例纪要】，分析它的段落结构（例如是否有“一、会议基本情况”、“二、议定事项”）、用词习惯和行文语气。
然后，请将【本次草稿】改写成一份正式的会议纪要，必须严格模仿【样例纪要】的格式和文风。

【样例纪要】：
{style_text}

【本次草稿】：
{draft_text}

请直接输出纪要正文："""
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    data = {
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    }
                    response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data)
                    response.raise_for_status()
                    ai_result = response.json()['choices'][0]['message']['content']
                    
                    st.success("生成完成！")
                    st.text_area("👇 生成的会议纪要", value=ai_result, height=300)
                    st.session_state['latest_minutes'] = ai_result
                    st.info("💡 你可以复制上方文本，或者前往左侧【4. 决议事项与任务提取】自动生成待办表。")
                except Exception as e:
                    st.error(f"调用失败，请检查 Key 或网络。错误信息：{e}")


# ================= 功能四：决议事项提取 =================
elif menu == "4. 决议事项与任务提取":
    st.header("🎯 决议事项自动提取与任务跟踪")
    st.markdown("从会议纪要中自动识别**工作事项、责任人、完成时限**，生成标准待办清单。")
    
    default_text = st.session_state.get('latest_minutes', '')
    minutes_text = st.text_area("📄 会议纪要内容", value=default_text, height=200, placeholder="请粘贴会议纪要...")
    
    if st.button("🔍 自动提取任务清单", type="primary"):
        if not api_key: 
            st.warning("⚠️ 请先在左侧侧边栏填写你的 API Key。")
        elif not minutes_text: 
            st.warning("请提供纪要内容。")
        else:
            with st.spinner("AI 正在扮演项目经理，识别关键任务..."):
                prompt = f"""你是一个专业的项目管理助手。请阅读以下会议纪要，提取出所有的“工作事项/任务”。
请务必以纯 CSV 格式输出（第一行是表头），包含四列：任务事项, 责任人/部门, 完成时限, 具体要求。
如果纪要中没有明确责任人，请填“未指定”；没有明确时间，请填“待定”。
不要输出任何多余的解释，只输出 CSV 文本。

【会议纪要】：
{minutes_text}"""
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    data = {
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    }
                    response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data)
                    response.raise_for_status()
                    
                    # 清理可能存在的 markdown 代码块符号，防止 pd.read_csv 报错
                    csv_result = response.json()['choices'][0]['message']['content']
                    csv_result = csv_result.replace("```csv", "").replace("```", "").strip()
                    
                    df = pd.read_csv(io.StringIO(csv_result))
                    
                    st.success("提取成功！已生成任务跟踪表。")
                    st.dataframe(df, use_container_width=True)
                    
                    csv_data = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 下载任务清单 (CSV)",
                        data=csv_data,
                        file_name='会议任务清单.csv',
                        mime='text/csv',
                    )
                    st.info("💡 你可以下载此表并发给行政部门，或者导入到公司的项目管理软件中。")
                except Exception as e:
                    st.error(f"提取失败，AI可能没按格式输出，请重试。错误信息：{e}")
