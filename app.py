# 注入全局 CSS 样式
st.markdown("""
<style>
    /* 1. 隐藏默认的顶部留白，给蓝条腾地方 */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* 2. 蓝条绝对霸占最顶部 100% 宽度，层级最高 */
    .top-global-bar {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 60px;
        z-index: 9999999; /* 层级极高，盖住一切 */
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    .top-global-bar h1 {
        color: white !important;
        margin: 0;
        font-size: 1.6rem;
        font-weight: 600;
    }

    /* 3. 侧边栏强行往下压 60px，给蓝条让路，并保持最高层级 */
    section[data-testid="stSidebar"] {
        top: 60px !important; 
        height: calc(100vh - 60px) !important;
        z-index: 999998 !important; 
    }
    
    /* 4. 折叠按钮（>>）往下挪一点，防止被蓝条挡住 */
    button[data-testid="stSidebarCollapseButton"] {
        margin-top: 60px !important; 
    }

    /* 5. 右侧主内容区也往下挪 60px */
    .block-container {
        padding-top: 5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# 渲染顶部绝对固定蓝条 (注意这里 class 名字改成了 top-global-bar)
st.markdown("""
<div class="top-global-bar">
    <h1>智能会议助手</h1>
</div>
""", unsafe_allow_html=True)
