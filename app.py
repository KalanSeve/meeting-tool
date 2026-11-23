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
    /* 1. 彻底清除 Streamlit 默认的顶部空白 */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    .block-container {
        padding-top: 4.5rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* 2. 绝对全屏宽度的固定横幅 */
    .global-fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;  /* 横跨整个屏幕宽度 */
        z-index: 999999;
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        padding: 16px 0;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    .global-fixed-header h1 {
        color: white !important;
        margin: 0;
        font-size: 1.8rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# 渲染固定横幅 (去掉了图标)
st.markdown("""
<div class="global-fixed-header">
    <h1>智能会议助手</h1>
</div>
""", unsafe_allow_html=True)

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

# ================= 侧边栏 =================
st.sidebar.header("功能导航")
menu = st.sidebar.radio("选择功能", ["1. 会议室申请", "2. 通知模板生成", "3. AI 纪要风格仿写", "4. 决议事项与任务提取"])

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ AI 引擎设置")
api_key = st.sidebar.text_input("DeepSeek API Key", type="password", help="填入你自己的 API Key，仅在当前会话有效。")

# ================= 功能一：会议室申请 =================
if menu == "1. 会议室申请":
    st.header("会议室申请")
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
        st.subheader("📅 会议室预约情况")
        
        today = datetime.now().date()
        default_start = today - timedelta(days=today.weekday())
        default_end = default_start + timedelta(days=6)
        
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
            df = pd.DataFrame(rows, columns=["ID", "会议室", "会议名称", "开始时间", "结束时间"])
            df.insert(0, "选择取消", False)
            
            st.caption("勾选第一列的复选框，然后点击下方按钮即可取消对应会议。")
            
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
                disabled=["会议室", "会议名称", "开始时间", "结束时间"]
            )
            
            selected_rows = edited_df[edited_df["选择取消"] == True]
            
            if not selected_rows.empty:
                if st.button("🗑️ 取消选中的会议", type="secondary"):
                    conn = sqlite3.connect('meeting.db')
                    c = conn.cursor()
                    for index, row in selected_rows.iterrows():
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
    st.header("会议通知与议程生成器")
    
    tab1, tab2 = st.tabs(["📝 快速文本通知", "📄 正式会议议程 (导出Word)"])
    
    with tab1:
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

    with tab2:
        st.markdown("请填写会议信息。系统将自动按《通知模板》格式排版。")
        
        col1, col2 = st.columns(2)
        with col1:
            w_company = st.text_input("公司名称", "陕西秦耀储能科技有限公司")
            w_title = st.text_input("会议名称", "EPC 结算计划及资金需求讨论会")
            w_time = st.text_input("会议时间", "2026年1月19日（星期一）下午18:30")
            w_room = st.text_input("会议地点", "项目公司大会议室")
            w_tx_id = st.text_input("线上会议（腾讯会议号）", "522-651-848")
        with col2:
            w_host = st.text_input("主持人", "张维纬")
            w_recorder = st.text_input("会议记录人", "董哲源")
            w_date_sign = st.text_input("落款日期", "2026年1月17日")
            
        w_attend = st.text_area("参会人员", "游平 武志涛 潘政 张中辉 韦永刚 张江峰 贾卫军 米美光", height=68)
            
        w_agenda = st.text_area("会议议程 (一行一项，无需输入序号)", "计划经营部对《进度结算指引》进行二次宣贯。\n地上EPC项目部汇报相关情况。\n地下EPC#1标段项目部汇报相关情况。\n地下EPC#2标段项目部汇报相关情况。\n各方就年前结算计划及资金需求进行讨论。\n领导总结发言。", height=200)

        if st.button("✨ 生成标准公文 Word", type="primary"):
            from docx import Document
            from docx.shared import Pt, Inches, Cm
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.oxml.ns import qn
            import io
            
            doc = Document()
            
            # 全局默认字体为仿宋_GB2312，三号字（16磅）
            doc.styles['Normal'].font.name = '仿宋_GB2312'
            doc.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋_GB2312')
            doc.styles['Normal'].font.size = Pt(16)

            # --- 标题部分 ---
            p_company = doc.add_paragraph()
            p_company.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_company.paragraph_format.space_after = Pt(0) 
            p_company.paragraph_format.space_before = Pt(0) 
            run_c = p_company.add_run(w_company)
            run_c.font.name = '方正小标宋简体'
            run_c._element.rPr.rFonts.set(qn('w:eastAsia'), '方正小标宋简体')
            run_c.font.size = Pt(22) # 二号字
            run_c.bold = False 
            
            p_title = doc.add_paragraph()
            p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_title.paragraph_format.space_after = Pt(0)
            p_title.paragraph_format.space_before = Pt(0)
            run_t = p_title.add_run(w_title)
            run_t.font.name = '方正小标宋简体'
            run_t._element.rPr.rFonts.set(qn('w:eastAsia'), '方正小标宋简体')
            run_t.font.size = Pt(22) # 二号字
            run_t.bold = False 
            
            doc.add_paragraph() 
            
            # 辅助函数：制表符对齐法（完美解决换行）
            def add_info_line(label, content):
                p = doc.add_paragraph()
                p.paragraph_format.line_spacing = 1.5 
                p.paragraph_format.space_after = Pt(0) 
                p.paragraph_format.space_before = Pt(0)
                
                # 关键点：使用 Tab 键对齐
                run_label = p.add_run(label + "\t")
                run_label.font.name = '黑体'
                run_label._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
                run_label.font.size = Pt(16) # 三号字
                run_label.bold = False
                
                # 设置制表位在 2.5 厘米处，这样换行后会自动和上一行的名字对齐
                p.paragraph_format.tab_stops.add_tab_stop(Cm(2.5))
                
                run_content = p.add_run(content.strip())
                run_content.font.name = '仿宋_GB2312'
                run_content._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋_GB2312')
                run_content.font.size = Pt(16)
                run_content.bold = False
                return p

            # --- 会议基础信息 ---
            add_info_line("会议时间：", w_time)
            add_info_line("会议地点：", w_room)
            if w_tx_id.strip():
                add_info_line("线上会议：", f"腾讯会议 {w_tx_id.strip()}")
            add_info_line("主持人：", w_host)
            add_info_line("参会人员：", w_attend)
            add_info_line("会议记录：", w_recorder)
                
            # --- 会议议程 ---
            doc.add_paragraph() 
            p_agenda_title = doc.add_paragraph()
            p_agenda_title.paragraph_format.line_spacing = 1.5
            p_agenda_title.paragraph_format.space_after = Pt(0)
            run_ag = p_agenda_title.add_run("会议议程：")
            run_ag.font.name = '黑体'
            run_ag._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
            run_ag.font.size = Pt(16)
            run_ag.bold = False
            
            chinese_nums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
            valid_agenda_items = [item.strip() for item in w_agenda.split('\n') if item.strip()]
            
            for i, item in enumerate(valid_agenda_items):
                p = doc.add_paragraph()
                p.paragraph_format.line_spacing = 1.5
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.left_indent = Cm(1.5) # 议程缩进
                
                num_str = chinese_nums[i] if i < len(chinese_nums) else str(i+1)
                run_item = p.add_run(f"（{num_str}）{item}")
                run_item.font.name = '仿宋_GB2312'
                run_item._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋_GB2312')
                run_item.font.size = Pt(16)
                run_item.bold = False
                    
            doc.add_paragraph() 
            doc.add_paragraph() 
            
            # --- 落款 ---
            p_sign_company = doc.add_paragraph()
            p_sign_company.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p_sign_company.paragraph_format.line_spacing = 1.5
            p_sign_company.paragraph_format.space_after = Pt(0)
            run_sc = p_sign_company.add_run(w_company)
            run_sc.font.name = '仿宋_GB2312'
            run_sc._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋_GB2312')
            run_sc.font.size = Pt(16)
            run_sc.bold = False
            
            p_sign_date = doc.add_paragraph()
            p_sign_date.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p_sign_date.paragraph_format.line_spacing = 1.5
            p_sign_date.paragraph_format.space_after = Pt(0)
            run_sd = p_sign_date.add_run(w_date_sign)
            run_sd.font.name = '仿宋_GB2312'
            run_sd._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋_GB2312')
            run_sd.font.size = Pt(16)
            run_sd.bold = False

            # 保存
            doc_io = io.BytesIO()
            doc.save(doc_io)
            doc_io.seek(0)

            st.success("Word 文档已生成！排版已严格按二号/三号字体及制表符对齐。")
            st.download_button(
                label="📥 下载会议通知 (.docx)",
                data=doc_io,
                file_name=f"{w_title}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )


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
                    
                    st.warning("⚠️ 人工审核卡点：由于大模型存在幻觉，请人工核对责任人、时间节点等关键事实，确认无误后方可正式发布。")
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
