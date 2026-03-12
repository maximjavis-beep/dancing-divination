# ML预测模型
"""
基于六爻卦象的神经网络预测模型
输入：卦象特征
输出：吉凶概率、事件类型、时间窗口
"""

import json
import os
import sys
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import pickle

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from liuyao.engine import TRIGRAMS

# 设置随机种子
torch.manual_seed(42)
np.random.seed(42)

class HexagramDataset(Dataset):
    """六爻数据集"""
    
    def __init__(self, cases, label_encoders=None):
        self.cases = cases
        
        # 初始化或复用label encoder
        if label_encoders is None:
            self.label_encoders = {
                'question_type': LabelEncoder(),
                'fortune_level': LabelEncoder(),
                'time_window': LabelEncoder(),
                'hexagram': LabelEncoder(),
                'upper_trigram': LabelEncoder(),
                'lower_trigram': LabelEncoder(),
            }
            self._fit_encoders()
        else:
            self.label_encoders = label_encoders
    
    def _fit_encoders(self):
        """拟合label encoders"""
        question_types = [c['question_type'] for c in self.cases]
        fortune_levels = [c['expert_interpretation']['fortune_level'] for c in self.cases]
        time_windows = [c['expert_interpretation']['time_window'] for c in self.cases]
        hexagrams = [c['hexagram']['name'] for c in self.cases]
        upper_trigrams = [c['hexagram']['upper_trigram'] for c in self.cases]
        lower_trigrams = [c['hexagram']['lower_trigram'] for c in self.cases]
        
        self.label_encoders['question_type'].fit(question_types)
        self.label_encoders['fortune_level'].fit(fortune_levels)
        self.label_encoders['time_window'].fit(time_windows)
        self.label_encoders['hexagram'].fit(hexagrams)
        self.label_encoders['upper_trigram'].fit(upper_trigrams)
        self.label_encoders['lower_trigram'].fit(lower_trigrams)
    
    def __len__(self):
        return len(self.cases)
    
    def __getitem__(self, idx):
        case = self.cases[idx]
        
        # 构建特征向量
        features = self._extract_features(case)
        
        # 标签
        fortune_label = self.label_encoders['fortune_level'].transform(
            [case['expert_interpretation']['fortune_level']]
        )[0]
        type_label = self.label_encoders['question_type'].transform(
            [case['question_type']]
        )[0]
        time_label = self.label_encoders['time_window'].transform(
            [case['expert_interpretation']['time_window']]
        )[0]
        
        return (
            torch.FloatTensor(features),
            torch.LongTensor([fortune_label])[0],
            torch.LongTensor([type_label])[0],
            torch.LongTensor([time_label])[0],
        )
    
    def _extract_features(self, case) -> np.ndarray:
        """从案例中提取特征向量"""
        features = []
        
        # 1. 时间特征 (4维)
        features.append(case['month'] / 12.0)
        features.append(case['day'] / 31.0)
        features.append(case['hour'] / 24.0)
        features.append((case['year'] - 2020) / 5.0)
        
        # 2. 问事类型 (one-hot, 5维)
        qtype_encoded = self.label_encoders['question_type'].transform([case['question_type']])[0]
        qtype_onehot = np.zeros(5)
        qtype_onehot[qtype_encoded] = 1
        features.extend(qtype_onehot)
        
        # 3. 卦象特征
        # 六爻 (6维)
        features.extend(case['hexagram']['lines'])
        
        # 动爻特征 (6维 one-hot)
        moving_onehot = np.zeros(6)
        for pos in case['hexagram']['moving_lines']:
            if 1 <= pos <= 6:
                moving_onehot[pos - 1] = 1
        features.extend(moving_onehot)
        
        # 4. 八卦五行编码 (8维 one-hot for upper, 8维 for lower)
        upper_encoded = self.label_encoders['upper_trigram'].transform(
            [case['hexagram']['upper_trigram']]
        )[0]
        lower_encoded = self.label_encoders['lower_trigram'].transform(
            [case['hexagram']['lower_trigram']]
        )[0]
        
        upper_onehot = np.zeros(8)
        lower_onehot = np.zeros(8)
        upper_onehot[upper_encoded] = 1
        lower_onehot[lower_encoded] = 1
        features.extend(upper_onehot)
        features.extend(lower_onehot)
        
        # 5. 世应位置 (2维)
        features.append(case['analysis']['shi_position'] / 6.0)
        features.append(case['analysis']['ying_position'] / 6.0)
        
        # 6. 五行关系编码 (5维 one-hot)
        element_relations = {'生': 0, '被生': 1, '克': 2, '被克': 3, '比和': 4}
        relation = case['analysis']['element_relation']
        relation_onehot = np.zeros(5)
        if relation in element_relations:
            relation_onehot[element_relations[relation]] = 1
        features.extend(relation_onehot)
        
        return np.array(features, dtype=np.float32)

class HexagramPredictor(nn.Module):
    """六爻预测神经网络"""
    
    def __init__(self, input_size=44, hidden_size=128, 
                 num_fortune_classes=5, num_type_classes=5, num_time_classes=5):
        super(HexagramPredictor, self).__init__()
        
        # 共享特征提取层
        self.shared = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.3),
        )
        
        # 吉凶预测头
        self.fortune_classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, num_fortune_classes),
        )
        
        # 事件类型预测头
        self.type_classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, num_type_classes),
        )
        
        # 时间窗口预测头
        self.time_classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, num_time_classes),
        )
    
    def forward(self, x):
        shared_features = self.shared(x)
        
        fortune_logits = self.fortune_classifier(shared_features)
        type_logits = self.type_classifier(shared_features)
        time_logits = self.time_classifier(shared_features)
        
        return fortune_logits, type_logits, time_logits

class PredictorModel:
    """预测模型包装类"""
    
    FORTUNE_LEVELS = ['大吉', '吉', '平', '凶', '大凶']
    QUESTION_TYPES = ['财运', '事业', '婚姻', '健康', '诉讼']
    TIME_WINDOWS = [
        '近期（3日内）',
        '短期（一周内）',
        '中期（一月内）',
        '长期（三月内）',
        '远期（半年内）',
    ]
    
    def __init__(self, model_path=None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.label_encoders = None
        self.model_path = model_path or os.path.join(
            os.path.dirname(__file__), 'hexagram_model.pt'
        )
        self.encoder_path = os.path.join(
            os.path.dirname(__file__), 'label_encoders.pkl'
        )
    
    def train(self, cases, epochs=100, batch_size=16, lr=0.001):
        """训练模型"""
        print(f"训练设备: {self.device}")
        
        # 划分训练集和验证集
        train_cases, val_cases = train_test_split(cases, test_size=0.2, random_state=42)
        
        # 创建数据集
        train_dataset = HexagramDataset(train_cases)
        val_dataset = HexagramDataset(val_cases, train_dataset.label_encoders)
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)
        
        # 保存label encoders
        self.label_encoders = train_dataset.label_encoders
        
        # 初始化模型
        input_size = len(train_dataset[0][0])
        self.model = HexagramPredictor(
            input_size=input_size,
            num_fortune_classes=len(self.FORTUNE_LEVELS),
            num_type_classes=len(self.QUESTION_TYPES),
            num_time_classes=len(self.TIME_WINDOWS),
        ).to(self.device)
        
        # 损失函数和优化器
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=lr)
        scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.5)
        
        # 训练循环
        best_val_loss = float('inf')
        for epoch in range(epochs):
            # 训练
            self.model.train()
            train_loss = 0
            for features, fortune_labels, type_labels, time_labels in train_loader:
                features = features.to(self.device)
                fortune_labels = fortune_labels.to(self.device)
                type_labels = type_labels.to(self.device)
                time_labels = time_labels.to(self.device)
                
                optimizer.zero_grad()
                
                fortune_logits, type_logits, time_logits = self.model(features)
                
                loss_fortune = criterion(fortune_logits, fortune_labels)
                loss_type = criterion(type_logits, type_labels)
                loss_time = criterion(time_logits, time_labels)
                
                loss = loss_fortune + loss_type + loss_time
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            scheduler.step()
            
            # 验证
            self.model.eval()
            val_loss = 0
            correct_fortune = 0
            correct_type = 0
            total = 0
            
            with torch.no_grad():
                for features, fortune_labels, type_labels, time_labels in val_loader:
                    features = features.to(self.device)
                    fortune_labels = fortune_labels.to(self.device)
                    type_labels = type_labels.to(self.device)
                    time_labels = time_labels.to(self.device)
                    
                    fortune_logits, type_logits, time_logits = self.model(features)
                    
                    loss_fortune = criterion(fortune_logits, fortune_labels)
                    loss_type = criterion(type_logits, type_labels)
                    loss_time = criterion(time_logits, time_labels)
                    
                    val_loss += (loss_fortune + loss_type + loss_time).item()
                    
                    _, predicted_fortune = torch.max(fortune_logits, 1)
                    _, predicted_type = torch.max(type_logits, 1)
                    
                    total += fortune_labels.size(0)
                    correct_fortune += (predicted_fortune == fortune_labels).sum().item()
                    correct_type += (predicted_type == type_labels).sum().item()
            
            train_loss /= len(train_loader)
            val_loss /= len(val_loader)
            fortune_acc = 100 * correct_fortune / total
            type_acc = 100 * correct_type / total
            
            if (epoch + 1) % 10 == 0:
                print(f'Epoch [{epoch+1}/{epochs}], '
                      f'Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}, '
                      f'Fortune Acc: {fortune_acc:.2f}%, Type Acc: {type_acc:.2f}%')
            
            # 保存最佳模型
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self.save_model()
        
        print(f"训练完成，最佳验证损失: {best_val_loss:.4f}")
    
    def predict(self, case_features: np.ndarray) -> dict:
        """预测单个案例"""
        if self.model is None:
            self.load_model()
        
        self.model.eval()
        with torch.no_grad():
            features = torch.FloatTensor(case_features).unsqueeze(0).to(self.device)
            fortune_logits, type_logits, time_logits = self.model(features)
            
            # 计算概率
            fortune_probs = torch.softmax(fortune_logits, dim=1)[0]
            type_probs = torch.softmax(type_logits, dim=1)[0]
            time_probs = torch.softmax(time_logits, dim=1)[0]
            
            # 获取预测结果
            fortune_pred = torch.argmax(fortune_probs).item()
            type_pred = torch.argmax(type_probs).item()
            time_pred = torch.argmax(time_probs).item()
            
            return {
                'fortune_level': self.FORTUNE_LEVELS[fortune_pred],
                'fortune_probabilities': {
                    level: fortune_probs[i].item() 
                    for i, level in enumerate(self.FORTUNE_LEVELS)
                },
                'question_type': self.QUESTION_TYPES[type_pred],
                'type_probabilities': {
                    t: type_probs[i].item()
                    for i, t in enumerate(self.QUESTION_TYPES)
                },
                'time_window': self.TIME_WINDOWS[time_pred],
                'time_probabilities': {
                    t: time_probs[i].item()
                    for i, t in enumerate(self.TIME_WINDOWS)
                },
            }
    
    def save_model(self):
        """保存模型"""
        if self.model is not None:
            torch.save(self.model.state_dict(), self.model_path)
            with open(self.encoder_path, 'wb') as f:
                pickle.dump(self.label_encoders, f)
            print(f"模型已保存至: {self.model_path}")
    
    def load_model(self):
        """加载模型"""
        if os.path.exists(self.model_path):
            with open(self.encoder_path, 'rb') as f:
                self.label_encoders = pickle.load(f)
            
            input_size = 44  # 默认特征维度
            self.model = HexagramPredictor(
                input_size=input_size,
                num_fortune_classes=len(self.FORTUNE_LEVELS),
                num_type_classes=len(self.QUESTION_TYPES),
                num_time_classes=len(self.TIME_WINDOWS),
            ).to(self.device)
            
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            self.model.eval()
            print(f"模型已加载: {self.model_path}")
        else:
            raise FileNotFoundError(f"模型文件不存在: {self.model_path}")

def train_model():
    """训练模型主函数"""
    # 加载数据
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cases.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)
    
    print(f"加载了 {len(cases)} 个案例")
    
    # 训练模型
    model = PredictorModel()
    model.train(cases, epochs=100, batch_size=16, lr=0.001)
    
    return model

if __name__ == '__main__':
    train_model()
