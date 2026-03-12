"""
深度学习预测模型 (DNN)
使用PyTorch构建深度神经网络
"""

import json
import os
import sys
import numpy as np
from typing import Dict, List
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from liuyao.engine import TRIGRAMS, LIUCHONG_HEXAGRAMS, LIUHE_HEXAGRAMS, YOUHUN_HEXAGRAMS, GUIHUN_HEXAGRAMS

class DNNHexagramPredictor(nn.Module):
    """深度神经网络六爻预测器"""
    
    FORTUNE_LEVELS = ['大吉', '吉', '平', '凶', '大凶']
    QUESTION_TYPES = ['财运', '事业', '婚姻', '健康', '诉讼']
    TIME_WINDOWS = [
        '近期（3日内）',
        '短期（一周内）',
        '中期（一月内）',
        '长期（三月内）',
        '远期（半年内）',
    ]
    
    def __init__(self, input_size=55, hidden_sizes=[128, 64, 32], num_classes=5, dropout=0.3):
        super(DNNHexagramPredictor, self).__init__()
        
        layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            layers.append(nn.BatchNorm1d(hidden_size))
            prev_size = hidden_size
        
        layers.append(nn.Linear(prev_size, num_classes))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)

class DNNPredictor:
    """DNN预测器封装"""
    
    def __init__(self, model_path=None):
        self.model_path = model_path or os.path.join(
            os.path.dirname(__file__), 'dnn_model.pt'
        )
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"使用设备: {self.device}")
    
    def _extract_features(self, case: Dict) -> np.ndarray:
        """从案例中提取特征（与GBM相同）"""
        features = []
        
        # 1. 时间特征 (4维)
        features.append(case['month'] / 12.0)
        features.append(case['day'] / 31.0)
        features.append(case['hour'] / 24.0)
        features.append((case['year'] - 2020) / 10.0)
        
        # 2. 问事类型 one-hot (5维)
        qtype_idx = self.QUESTION_TYPES.index(case['question_type'])
        qtype_onehot = [1 if i == qtype_idx else 0 for i in range(5)]
        features.extend(qtype_onehot)
        
        # 3. 六爻特征 (6维)
        features.extend(case['hexagram']['lines'])
        
        # 4. 动爻 one-hot (6维)
        moving_onehot = [0] * 6
        for pos in case['hexagram']['moving_lines']:
            if 1 <= pos <= 6:
                moving_onehot[pos - 1] = 1
        features.extend(moving_onehot)
        
        # 5. 上下卦 one-hot (8+8=16维)
        upper_idx = list(TRIGRAMS.keys()).index(case['hexagram']['upper_trigram'])
        lower_idx = list(TRIGRAMS.keys()).index(case['hexagram']['lower_trigram'])
        
        upper_onehot = [1 if i == upper_idx else 0 for i in range(8)]
        lower_onehot = [1 if i == lower_idx else 0 for i in range(8)]
        features.extend(upper_onehot)
        features.extend(lower_onehot)
        
        # 6. 世应位置 (2维)
        features.append(case['analysis']['shi_position'] / 6.0)
        features.append(case['analysis']['ying_position'] / 6.0)
        
        # 7. 五行关系 one-hot (5维)
        element_relations = {'生': 0, '被生': 1, '克': 2, '被克': 3, '比和': 4}
        relation = case['analysis']['element_relation']
        relation_idx = element_relations.get(relation, 4)
        relation_onehot = [1 if i == relation_idx else 0 for i in range(5)]
        features.extend(relation_onehot)
        
        # 8. 动爻数量 (1维)
        features.append(len(case['hexagram']['moving_lines']) / 6.0)
        
        # 9. 是否有动爻 (1维)
        features.append(1 if case['hexagram']['moving_lines'] else 0)
        
        # 10. 六冲/六合/游魂/归魂特征 (4维)
        hexagram_name = case['hexagram'].get('name', '')
        features.append(1 if hexagram_name in LIUCHONG_HEXAGRAMS else 0)
        features.append(1 if hexagram_name in LIUHE_HEXAGRAMS else 0)
        features.append(1 if hexagram_name in YOUHUN_HEXAGRAMS else 0)
        features.append(1 if hexagram_name in GUIHUN_HEXAGRAMS else 0)
        
        # 11. 特殊格局 one-hot (5维)
        if hexagram_name in LIUCHONG_HEXAGRAMS:
            special_pattern = '六冲'
        elif hexagram_name in LIUHE_HEXAGRAMS:
            special_pattern = '六合'
        elif hexagram_name in YOUHUN_HEXAGRAMS:
            special_pattern = '游魂'
        elif hexagram_name in GUIHUN_HEXAGRAMS:
            special_pattern = '归魂'
        else:
            special_pattern = '普通'
        
        pattern_types = ['普通', '六冲', '六合', '游魂', '归魂']
        pattern_idx = pattern_types.index(special_pattern) if special_pattern in pattern_types else 0
        pattern_onehot = [1 if i == pattern_idx else 0 for i in range(5)]
        features.extend(pattern_onehot)
        
        return np.array(features, dtype=np.float32)
    
    def prepare_data(self, cases: List[Dict]):
        """准备训练数据"""
        X = []
        y = []
        
        for case in cases:
            features = self._extract_features(case)
            X.append(features)
            y.append(self.FORTUNE_LEVELS.index(
                case['expert_interpretation']['fortune_level']
            ))
        
        return np.array(X), np.array(y)
    
    def train(self, cases, epochs=100, batch_size=32, lr=0.001, patience=10):
        """训练DNN模型"""
        X, y = self.prepare_data(cases)
        
        # 划分训练集和验证集
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # 转换为Tensor
        X_train = torch.FloatTensor(X_train).to(self.device)
        y_train = torch.LongTensor(y_train).to(self.device)
        X_val = torch.FloatTensor(X_val).to(self.device)
        y_val = torch.LongTensor(y_val).to(self.device)
        
        # 创建数据加载器
        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        # 初始化模型
        input_size = X.shape[1]
        num_classes = len(self.FORTUNE_LEVELS)
        self.model = DNNHexagramPredictor(input_size=input_size, num_classes=num_classes).to(self.device)
        
        # 损失函数和优化器
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=lr, weight_decay=1e-5)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
        
        # 训练
        best_val_acc = 0
        patience_counter = 0
        
        print(f"\\n开始训练DNN模型...")
        print(f"训练集大小: {len(X_train)}, 验证集大小: {len(X_val)}")
        
        for epoch in range(epochs):
            self.model.train()
            train_loss = 0
            correct = 0
            total = 0
            
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()
            
            train_acc = correct / total
            
            # 验证
            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(X_val)
                val_loss = criterion(val_outputs, y_val).item()
                _, val_predicted = torch.max(val_outputs.data, 1)
                val_acc = (val_predicted == y_val).sum().item() / len(y_val)
            
            scheduler.step(val_loss)
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs}: Train Acc={train_acc:.2%}, Val Acc={val_acc:.2%}")
            
            # 早停
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
                # 保存最佳模型
                torch.save(self.model.state_dict(), self.model_path)
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"\\n早停于 Epoch {epoch+1}, 最佳验证准确率: {best_val_acc:.2%}")
                    break
        
        # 加载最佳模型
        self.model.load_state_dict(torch.load(self.model_path))
        print(f"\\nDNN模型训练完成，最佳验证准确率: {best_val_acc:.2%}")
        
        return {'val_accuracy': best_val_acc}
    
    def predict(self, case: Dict) -> Dict:
        """预测单个案例"""
        if self.model is None:
            self.load_model()
        
        self.model.eval()
        features = self._extract_features(case).reshape(1, -1)
        features = torch.FloatTensor(features).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(features)
            probabilities = torch.softmax(outputs, dim=1).cpu().numpy()[0]
            prediction = np.argmax(probabilities)
        
        return {
            'fortune_level': self.FORTUNE_LEVELS[prediction],
            'fortune_probabilities': {
                level: float(probabilities[i])
                for i, level in enumerate(self.FORTUNE_LEVELS)
            },
        }
    
    def load_model(self):
        """加载模型"""
        if os.path.exists(self.model_path):
            input_size = 55  # 默认特征数
            num_classes = len(self.FORTUNE_LEVELS)
            self.model = DNNHexagramPredictor(input_size=input_size, num_classes=num_classes).to(self.device)
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            self.model.eval()
            print(f"DNN模型已加载: {self.model_path}")
        else:
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")

def train_dnn_model():
    """训练DNN模型主函数"""
    # 加载数据
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cases.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        mock_cases = json.load(f)
    
    gudian_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gudian_cases.json')
    with open(gudian_path, 'r', encoding='utf-8') as f:
        gudian_cases = json.load(f)
    
    cases = mock_cases + gudian_cases
    print(f"总案例数: {len(cases)}")
    
    # 训练模型
    model = DNNPredictor()
    results = model.train(cases, epochs=200, batch_size=64, lr=0.001, patience=20)
    
    print(f"\\n训练完成!")
    print(f"验证准确率: {results['val_accuracy']:.2%}")
    
    return model

if __name__ == '__main__':
    train_dnn_model()
