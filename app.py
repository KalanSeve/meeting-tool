# 注入全局 CSS 样式
st.markdown("""
<style>
    /* 1. 核心：只把原生顶栏变透明，不要 display: none，否则折叠按钮会消失 */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }
    
    /* 隐藏右上角自带的 Share、GitHub 等小图标，让蓝条更干净 */
    div[data-testid="stStatusWidget"] { display: none !important; }
    header[data-testid="stHeader"] div[data-testid="stToolbar"] { display: none !important; }

    /* 2. 蓝条样式：加大高度到 80px */
    .right-fixed-header {
        position: fixed;
        top: 0;
        left: 21rem; /* 避开侧边栏 */
        right: 0;
        height: 80px; /* 高度加大 */
        z-index: 99999;
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .right-fixed-header h1 {
        color: white !important;
        margin: 0;
        font-size: 2.2rem; /* 字体稍微放大 */
        font-weight: 600;
        letter-spacing: 2px; /* 增加字间距，显得更大气 */
    }

    /* 3. 监听侧边栏折叠状态：折叠时蓝条自动贴边 */
    section[data-testid="stSidebar"][aria-expanded="false"] + div .right-fixed-header {
        left: 0 !important;
        transition: left 0.3s ease;
    }

    /* 4. 给主内容区留出空间，因为蓝条变高了，这里也要同步加大 */
    .block-container {
        padding-top: 6.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# 渲染固定蓝条
st.markdown("""
<div class="right-fixed-header">
    <h1>AI 智能会议助手</h1>
</div>
""", unsafe_allow_html=True)
