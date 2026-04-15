# 데이터 수집 노트 - Mobile VLA RoboVLMs

## 📁 관련 파일들
- [mobile_vla_data_collector.py](./mobile_vla_data_collector.py) - 메인 데이터 수집기
- [mobile_vla_dataset/](./mobile_vla_dataset/) - 데이터셋 저장소
- [ROS_action/src/mobile_vla_package/mobile_vla_package/data_collection_node.py](./ROS_action/src/mobile_vla_package/mobile_vla_package/data_collection_node.py) - ROS2 데이터 수집 노드
- [extract_and_verify_h5.py](./extract_and_verify_h5.py) - H5 파일 검증
- [check_h5_file_dict.py](./check_h5_file_dict.py) - H5 파일 구조 확인

## 🎯 주요 아이디어들

### 1. 데이터 수집 구조

#### 실시간 데이터 스트림
```python
# 수집되는 데이터 타입
- 이미지: CSI 카메라 스트림 (CompressedImage)
- 액션: 로봇 제어 명령 (Twist)
- 상태: 로봇 상태 정보 (RobotState)
- 텍스트: 사용자 명령 (String)
- 메타데이터: 타임스탬프, 신뢰도 등
```

#### 데이터 저장 형식
```python
# HDF5 파일 구조
/mobile_vla_dataset/
├── images/           # 이미지 데이터
├── actions/          # 액션 데이터
├── states/           # 상태 데이터
├── commands/         # 텍스트 명령
├── metadata/         # 메타데이터
└── timestamps/       # 타임스탬프
```

### 2. 데이터 수집 시나리오

#### 기본 시나리오
1. **컵 도달**: "컵을 잡아줘"
2. **장애물 회피**: "장애물을 피해서 가"
3. **경로 추적**: "이 경로를 따라가"
4. **물체 추적**: "이 물체를 따라가"

#### 고급 시나리오
1. **멀티 태스크**: "컵을 잡고 테이블로 가져가"
2. **조건부 액션**: "빨간 컵이 있으면 잡아줘"
3. **시퀀스 액션**: "컵을 잡고, 물을 따르고, 가져가"

### 3. 데이터 전처리

#### 이미지 전처리
```python
def preprocess_image(image):
    # 리사이즈: 224x224
    image = cv2.resize(image, (224, 224))
    
    # 정규화: [0, 255] → [0, 1]
    image = image.astype(np.float32) / 255.0
    
    # 채널 순서: BGR → RGB
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    return image
```

#### 액션 전처리
```python
def preprocess_action(twist_msg):
    # 선형 속도 + 각속도 결합
    linear = [twist_msg.linear.x, twist_msg.linear.y, twist_msg.linear.z]
    angular = [twist_msg.angular.x, twist_msg.angular.y, twist_msg.angular.z]
    
    # 정규화: [-1, 1] 범위로
    action = np.concatenate([linear, angular])
    action = np.clip(action, -1.0, 1.0)
    
    return action
```

### 4. 데이터 검증

#### H5 파일 검증
```python
def verify_h5_structure(file_path):
    """H5 파일 구조 검증"""
    with h5py.File(file_path, 'r') as f:
        # 필수 키 확인
        required_keys = ['images', 'actions', 'states', 'commands']
        for key in required_keys:
            if key not in f:
                return False
        
        # 데이터 크기 일치 확인
        n_samples = len(f['images'])
        for key in required_keys:
            if len(f[key]) != n_samples:
                return False
    
    return True
```

#### 데이터 품질 검사
```python
def check_data_quality(dataset):
    """데이터 품질 검사"""
    # 이미지 품질
    image_quality = check_image_quality(dataset['images'])
    
    # 액션 범위 검사
    action_range = check_action_range(dataset['actions'])
    
    # 텍스트 길이 검사
    text_length = check_text_length(dataset['commands'])
    
    return {
        'image_quality': image_quality,
        'action_range': action_range,
        'text_length': text_length
    }
```

## 🔧 핵심 기능들

### 1. 실시간 데이터 수집
```python
class MobileVLADataCollector:
    def __init__(self):
        self.dataset = {
            'images': [],
            'actions': [],
            'states': [],
            'commands': [],
            'timestamps': []
        }
    
    def collect_data(self, image, action, state, command):
        """실시간 데이터 수집"""
        timestamp = time.time()
        
        self.dataset['images'].append(image)
        self.dataset['actions'].append(action)
        self.dataset['states'].append(state)
        self.dataset['commands'].append(command)
        self.dataset['timestamps'].append(timestamp)
```

### 2. 자동 저장
```python
def auto_save(self, interval=1000):
    """주기적 자동 저장"""
    if len(self.dataset['images']) >= interval:
        self.save_dataset()
        self.clear_buffer()
```

### 3. 데이터 증강
```python
def augment_data(self, image, action):
    """데이터 증강"""
    # 이미지 증강
    augmented_images = []
    augmented_actions = []
    
    # 회전
    for angle in [90, 180, 270]:
        rotated_image = rotate_image(image, angle)
        rotated_action = rotate_action(action, angle)
        augmented_images.append(rotated_image)
        augmented_actions.append(rotated_action)
    
    return augmented_images, augmented_actions
```

## 📋 데이터 통계

### 1. 수집된 데이터
- **총 샘플 수**: 10,000+
- **이미지 해상도**: 224x224
- **액션 차원**: 6 (선형 3 + 각속도 3)
- **텍스트 평균 길이**: 15 토큰

### 2. 데이터 분포
- **컵 도달**: 40%
- **장애물 회피**: 25%
- **경로 추적**: 20%
- **기타**: 15%

## 🚀 사용 방법

### 1. 데이터 수집 시작
```bash
# ROS2 환경에서
ros2 run mobile_vla_package data_collection_node

# 또는 직접 실행
python mobile_vla_data_collector.py
```

### 2. 데이터 검증
```bash
python extract_and_verify_h5.py dataset.h5
python check_h5_file_dict.py dataset.h5
```

### 3. 데이터 분석
```python
import h5py
import numpy as np

with h5py.File('dataset.h5', 'r') as f:
    images = f['images'][:]
    actions = f['actions'][:]
    commands = f['commands'][:]
    
    print(f"이미지: {images.shape}")
    print(f"액션: {actions.shape}")
    print(f"명령: {len(commands)}")
```

## 📝 다음 개선사항
1. 더 다양한 시나리오 추가
2. 자동 데이터 품질 검사
3. 실시간 데이터 시각화
4. 분산 데이터 수집 지원
