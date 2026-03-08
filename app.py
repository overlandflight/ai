# app.py - 千问API版财经日报（适配Railway）
from flask import Flask, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from openai import OpenAI
import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)

# 从环境变量读取API Key（Railway中设置）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")

# 千问API配置
BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"  # 国际版接入点
MODEL_NAME = "qwen3.5-plus"  # 使用最新Plus模型

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=BASE_URL
)

REPORT_FILE = 'daily_report.json'

def generate_daily_report():
    """调用千问API生成今日财经热点速递"""
    prompt = """请生成今日《每日财经热点速递》，要求包含以下板块：
1. 【全球动态要闻】：3-5条国际财经要闻及影响
2. 【国内市场行情】：A股/港股表现、领涨板块、资金流向
3. 【公司动态】：3-5家重要公司动态
4. 【热点前瞻】：未来1-2天潜在热点

请用专业且清晰的语言输出，每条信息后简要分析影响。"""
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "你是一位资深财经分析师，擅长从海量信息中提炼核心要点，生成专业的财经日报。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        content = completion.choices[0].message.content
        
        report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'content': content,
            'generated_time': datetime.now().isoformat()
        }
        return report
        
    except Exception as e:
        logging.error(f"API调用失败: {e}")
        return None

def save_report(report):
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

def load_report():
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def scheduled_job():
    logging.info("开始执行定时生成任务")
    report = generate_daily_report()
    if report:
        save_report(report)
        logging.info("日报生成成功")
    else:
        logging.error("日报生成失败")

# 定时任务：每天8:30执行
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_job, 'cron', hour=8, minute=30)
scheduler.start()

@app.route('/')
def home():
    return "千问财经日报服务运行中 - 访问 /api/daily-report 获取最新日报"

@app.route('/api/daily-report', methods=['GET'])
def get_report():
    report = load_report()
    if report:
        return jsonify({'success': True, 'data': report})
    else:
        # 如果没有日报，立即生成一份
        report = generate_daily_report()
        if report:
            save_report(report)
            return jsonify({'success': True, 'data': report})
        else:
            return jsonify({'success': False, 'message': '生成失败'}), 500

if __name__ == '__main__':
    # 启动时立即生成一份初始日报
    if not os.path.exists(REPORT_FILE):
        scheduled_job()
    app.run(host='0.0.0.0', port=5000)