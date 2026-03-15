from flask import Flask, render_template, jsonify, request
import json
import os
import sys
import random
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from liuyao.engine import LiuYaoEngine, generate_hexagram, analyze
from liuyao.bazi import calculate_bazi, get_bazi_info
from liuyao.bazi_hexagram import analyze_bazi_hexagram
from liuyao.trend_analyzer import analyze_trend
from liuyao.baihua import generate_full_baihua, get_hexagram_baihua

from model.gbm_predictor import GBMHexagramPredictor
from model.enhanced_gbm_predictor import EnhancedGBMPredictor
from model.performance_utils import get_cache, get_loader, cached_predict

app = Flask(__name__, 
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
)

# 初始化引擎和模型
engine = LiuYaoEngine()

# 优先使用增强版模型，如不存在则使用基础版
model = EnhancedGBMPredictor()
try:
    model.load_model()
    print("✅ 增强版模型加载成功")
except FileNotFoundError:
    print("⚠️ 增强版模型不存在，使用基础版模型")
    model = GBMHexagramPredictor()
    try:
        model.load_model()
    except:
        pass

# 使用懒加载数据加载器
loader = get_loader()
model_loaded = True
print(f"✅ 模型加载成功，数据案例: {len(loader.all_cases)} 个")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/divine', methods=['POST'])
def divine():
    """起卦接口"""
    data = request.json
    
    # 获取时间参数
    if 'datetime' in data and data['datetime']:
        dt = datetime.fromisoformat(data['datetime'].replace('Z', '+00:00'))
        year, month, day, hour = dt.year, dt.month, dt.day, dt.hour
    else:
        now = datetime.now()
        year, month, day, hour = now.year, now.month, now.day, now.hour
    
    question_type = data.get('question_type', '财运')
    
    # 生成卦象
    hexagram = generate_hexagram(year, month, day, hour)
    analysis = analyze(year, month, day, hour, question_type)
    
    # 构建案例特征用于预测
    case = {
        'year': year,
        'month': month,
        'day': day,
        'hour': hour,
        'question_type': question_type,
        'hexagram': {
            'name': hexagram.name,
            'upper_trigram': hexagram.upper_trigram,
            'lower_trigram': hexagram.lower_trigram,
            'lines': hexagram.lines,
            'moving_lines': hexagram.moving_lines,
        },
        'analysis': {
            'shi_position': analysis['世应']['世爻'],
            'ying_position': analysis['世应']['应爻'],
            'element_relation': analysis['本卦']['五行关系'],
        }
    }
    
    # AI 预测（使用混合模型）
    try:
        prediction = model.predict(case, return_components=True)
        # 转换概率格式以兼容前端
        prediction['fortune_probabilities'] = prediction['probabilities']
    except Exception as e:
        print(f"预测失败: {e}")
        prediction = generate_random_prediction()
    
    # 查找相似案例
    similar_cases = find_similar_cases(hexagram.name, question_type, limit=3)
    
    return jsonify({
        'success': True,
        'hexagram': {
            'name': hexagram.name,
            'upper_trigram': hexagram.upper_trigram,
            'lower_trigram': hexagram.lower_trigram,
            'upper_symbol': engine.trigrams[hexagram.upper_trigram]['symbol'],
            'lower_symbol': engine.trigrams[hexagram.lower_trigram]['symbol'],
            'lines': hexagram.lines,
            'moving_lines': hexagram.moving_lines,
        },
        'changed_hexagram': {
            'name': analysis['变卦']['卦名'],
            'upper_trigram': analysis['变卦']['上卦'],
            'lower_trigram': analysis['变卦']['下卦'],
        },
        'analysis': analysis,
        'prediction': prediction,
        'similar_cases': similar_cases,
        'timestamp': datetime.now().isoformat(),
    })

def generate_random_prediction():
    """生成随机预测（演示用）"""
    fortune_levels = ['大吉', '吉', '平', '凶', '大凶']
    time_windows = ['近期（3日内）', '短期（一周内）', '中期（一月内）', '长期（三月内）', '远期（半年内）']
    
    fortune = random.choice(fortune_levels)
    time_window = random.choice(time_windows)
    
    return {
        'fortune_level': fortune,
        'fortune_probabilities': {f: random.random() for f in fortune_levels},
        'time_window': time_window,
        'time_probabilities': {t: random.random() for t in time_windows},
        'note': '演示模式：模型未训练或加载失败'
    }

@app.route('/api/bazi', methods=['POST'])
def calculate_bazi_api():
    """计算八字接口"""
    data = request.json
    
    year = data.get('year', 1990)
    month = data.get('month', 1)
    day = data.get('day', 1)
    hour = data.get('hour', 12)
    gender = data.get('gender', '男')
    
    try:
        bazi_info = get_bazi_info(year, month, day, hour, gender)
        return jsonify({
            'success': True,
            'bazi': bazi_info,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 400

@app.route('/api/divine_with_bazi', methods=['POST'])
def divine_with_bazi():
    """八字六爻联合分析接口"""
    data = request.json
    
    # 出生时间（八字）
    birth = data.get('birth', {})
    birth_year = birth.get('year', 1990)
    birth_month = birth.get('month', 1)
    birth_day = birth.get('day', 1)
    birth_hour = birth.get('hour', 12)
    gender = data.get('gender', '男')
    
    # 起卦时间
    if 'datetime' in data and data['datetime']:
        dt = datetime.fromisoformat(data['datetime'].replace('Z', '+00:00'))
        div_year, div_month, div_day, div_hour = dt.year, dt.month, dt.day, dt.hour
    else:
        now = datetime.now()
        div_year, div_month, div_day, div_hour = now.year, now.month, now.day, now.hour
    
    question_type = data.get('question_type', '财运')
    
    try:
        # 联合分析
        result = analyze_bazi_hexagram(
            {'year': birth_year, 'month': birth_month, 'day': birth_day, 'hour': birth_hour},
            gender,
            {'year': div_year, 'month': div_month, 'day': div_day, 'hour': div_hour},
            question_type
        )
        
        # 同时获取AI预测
        hexagram = generate_hexagram(div_year, div_month, div_day, div_hour)
        case = {
            'year': div_year, 'month': div_month, 'day': div_day, 'hour': div_hour,
            'question_type': question_type,
            'hexagram': {
                'name': hexagram.name,
                'upper_trigram': hexagram.upper_trigram,
                'lower_trigram': hexagram.lower_trigram,
                'lines': hexagram.lines,
                'moving_lines': hexagram.moving_lines,
            },
            'analysis': {
                'shi_position': result['六爻']['世应']['世爻'],
                'ying_position': result['六爻']['世应']['应爻'],
                'element_relation': result['六爻']['本卦']['五行关系'],
            }
        }
        
        # AI 预测（使用混合模型）
        try:
            prediction = model.predict(case, return_components=True)
            # 转换概率格式以兼容前端
            prediction['fortune_probabilities'] = prediction['probabilities']
        except Exception as e:
            print(f"预测失败: {e}")
            prediction = generate_random_prediction()
        
        return jsonify({
            'success': True,
            'hexagram': {
                'name': hexagram.name,
                'upper_trigram': hexagram.upper_trigram,
                'lower_trigram': hexagram.lower_trigram,
                'upper_symbol': engine.trigrams[hexagram.upper_trigram]['symbol'],
                'lower_symbol': engine.trigrams[hexagram.lower_trigram]['symbol'],
                'lines': hexagram.lines,
                'moving_lines': hexagram.moving_lines,
            },
            'changed_hexagram': {
                'name': result['六爻']['变卦']['卦名'],
                'upper_trigram': result['六爻']['变卦']['上卦'],
                'lower_trigram': result['六爻']['变卦']['下卦'],
            },
            'bazi': result['八字'],
            'liuyao': result['六爻'],
            'combined_analysis': result['联合分析'],
            'prediction': prediction,
            'timestamp': datetime.now().isoformat(),
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
        }), 400

def find_similar_cases(hexagram_name, question_type, limit=3):
    """查找相似案例 - 使用懒加载"""
    matching = loader.get_cases_by_hexagram(hexagram_name) + loader.get_cases_by_type(question_type)
    
    if len(matching) < limit:
        matching = loader.all_cases
    
    selected = random.sample(matching, min(limit, len(matching)))
    
    return [{
        'case_id': c['case_id'],
        'hexagram_name': c['hexagram']['name'],
        'question_type': c['question_type'],
        'fortune_level': c['expert_interpretation']['fortune_level'],
        'time_window': c['expert_interpretation']['time_window'],
        'comment': c['expert_interpretation']['fortune_comment'],
    } for c in selected]

@app.route('/api/cases', methods=['GET'])
def get_cases():
    """获取案例列表"""
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    question_type = request.args.get('type', None)
    
    filtered = loader.all_cases
    if question_type:
        filtered = [c for c in loader.all_cases if c['question_type'] == question_type]
    
    total = len(filtered)
    paginated = filtered[offset:offset+limit]
    
    return jsonify({
        'success': True,
        'total': total,
        'cases': paginated,
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    # 统计各卦出现频率
    hexagram_counts = {}
    fortune_counts = {}
    type_counts = {}
    
    for c in loader.all_cases:
        name = c['hexagram']['name']
        hexagram_counts[name] = hexagram_counts.get(name, 0) + 1
        
        fortune = c['expert_interpretation']['fortune_level']
        fortune_counts[fortune] = fortune_counts.get(fortune, 0) + 1
        
        qtype = c['question_type']
        type_counts[qtype] = type_counts.get(qtype, 0) + 1
    
    return jsonify({
        'success': True,
        'total_cases': len(loader.all_cases),
        'hexagram_distribution': hexagram_counts,
        'fortune_distribution': fortune_counts,
        'question_type_distribution': type_counts,
        'model_loaded': model_loaded,
    })

@app.route('/api/baihua', methods=['POST'])
def get_baihua():
    """获取卦象白话解读"""
    data = request.json
    
    hexagram_name = data.get('hexagram_name', '乾为天')
    deity_type = data.get('deity_type', '妻财')
    question_type = data.get('question_type', '财运')
    moving_lines = data.get('moving_lines', [])
    
    try:
        baihua = generate_full_baihua(hexagram_name, deity_type, question_type, moving_lines)
        return jsonify({
            'success': True,
            'baihua': baihua,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 400

@app.route('/api/share', methods=['POST'])
def generate_share():
    """生成分享内容"""
    data = request.json
    
    hexagram_name = data.get('hexagram_name', '')
    fortune_level = data.get('fortune_level', '')
    question_type = data.get('question_type', '')
    best_time = data.get('best_time', '')
    summary = data.get('summary', '')
    
    # 生成分享文本
    share_text = f"""🔮 Dancing 卦象分享
━━━━━━━━━━━━━━
问: {question_type}
卦: {hexagram_name}
断: {fortune_level}
{best_time}

{summary}
━━━━━━━━━━━━━━
来自 Dancing 六爻预测系统"""
    
    return jsonify({
        'success': True,
        'share_text': share_text,
        'share_data': {
            'hexagram_name': hexagram_name,
            'fortune_level': fortune_level,
            'question_type': question_type,
            'best_time': best_time,
            'summary': summary,
        }
    })

@app.route('/api/trend', methods=['POST'])
def get_trend():
    """获取12小时卦象趋势分析"""
    data = request.json
    
    # 获取基准时间
    if 'datetime' in data and data['datetime']:
        dt = datetime.fromisoformat(data['datetime'].replace('Z', '+00:00'))
    else:
        dt = datetime.now()
    
    question_type = data.get('question_type', '财运')
    
    # 八字信息（可选）
    birth = data.get('birth', {})
    birth_info = None
    if birth:
        birth_info = {
            'year': birth.get('year'),
            'month': birth.get('month'),
            'day': birth.get('day'),
            'hour': birth.get('hour'),
        }
    gender = data.get('gender', '男')
    
    try:
        # 分析趋势
        trend_result = analyze_trend(
            engine, model, dt, question_type, birth_info, gender
        )
        
        return jsonify({
            'success': True,
            'trend': trend_result,
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
        }), 400

# Vercel serverless handler
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
else:
    # For Vercel
    application = app
