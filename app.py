import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import requests
import pandas as pd
import io

# ================= 页面基础设置 =================
st.set_page_config(page_title="智能会议助手", page_icon="📅", layout="wide")
st.title("📅 智能会议助手 (AI 办公流闭环)")

# ================= 数据库初始化 =================
def init_db():
    conn = sqlite3.connect('meeting.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bookings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  room TEXT, title TEXT, start_time TEXT, end_time TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ================= 顶部导航栏 =================
menu = st.sidebar.radio("功能导航", ["1. 会议室预约", "2. 通知模板生成", "3. AI 纪要风格仿写", "4. 决议事项与任务提取"])

# ================= 功能一：会议室预约 =================
if menu == "1. 会议室预约":
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
        if st.button("提交预约", type="primary", use_container_width=True):
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
                    c.execute("INSERT INTO bookings (room, title, start_time, end_time) VALUES (?, ?, ?, ?)", (room, title, start_str, end_str))
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
        c.execute("SELECT room, title, start_time, end_time FROM bookings WHERE date(start_time) >= ? AND date(start_time) <= ? ORDER BY start_time", (str(start_of_week), str(end_of_week)))
        rows = c.fetchall()
        conn.close()
        
        if rows:
            df = pd.DataFrame(rows, columns=["会议室", "会议名称", "开始时间", "结束时间"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("本周暂无会议安排，所有会议室均空闲。")
            
        if st.button("🗑️ 清空历史测试数据"):
            conn = sqlite3.connect('meeting.db')
            c = conn.cursor()
            c.execute("DELETE FROM bookings")
            conn.commit()
            conn.close()
            st.rerun()

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
    
    api_key = st.text_input("请输入你的大模型 API Key", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        style_text = st.text_area("📚 历史纪要样例（风格与结构参考）", height=250, placeholder="粘贴一段以前的优秀纪要...")
    with col2:
        draft_text = st.text_area("📝 本次会议草稿/录音转写要点", height=250, placeholder="粘贴本次会议的零散记录...")
    
    if st.button("✨ 一键生成正式纪要", type="primary"):
        if not api_key: 
            st.warning("请先填写 API Key。")
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
                    st.error(f"调用失败：{e}")


# ================= 功能四：决议事项提取 =================
elif menu == "4. 决议事项与任务提取":
    st.header("🎯 决议事项自动提取与任务跟踪")
    st.markdown("从会议纪要中自动识别**工作事项、责任人、完成时限**，生成标准待办清单。")
    
    api_key = st.text_input("请输入你的大模型 API Key", type="password")
    
    default_text = st.session_state.get('latest_minutes', '')
    minutes_text = st.text_area("📄 会议纪要内容", value=default_text, height=200, placeholder="请粘贴会议纪要...")
    
    if st.button("🔍 自动提取任务清单", type="primary"):
        if not api_key: 
            st.warning("请先填写 API Key。")
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