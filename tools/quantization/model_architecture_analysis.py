#!/usr/bin/env python3
"""
모델 구조 분석 - VLM, RoboVLMs, LSTM Layer 차이점 분석
"""

import torch
import torch.nn as nn
import json
import os
from typing import Dict, Any, List

class ModelArchitectureAnalyzer:
    """모델 구조 분석기"""
    
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"🔧 Device: {self.device}")
    
    def analyze_checkpoint_structure(self, checkpoint_path: str) -> Dict[str, Any]:
        """체크포인트 구조 분석"""
        print(f"\n📊 Analyzing checkpoint: {checkpoint_path}")
        print("-" * 60)
        
        try:
            # 체크포인트 로드
            checkpoint = torch.load(checkpoint_path, map_location='cpu')
            
            # 기본 정보
            info = {
                'file_size_mb': os.path.getsize(checkpoint_path) / (1024 * 1024),
                'checkpoint_keys': list(checkpoint.keys()),
                'model_state_dict_keys': [],
                'model_type': 'Unknown',
                'architecture_components': [],
                'parameter_count': 0,
                'kosmos2_components': [],
                'clip_components': [],
                'lstm_components': [],
                'vision_components': [],
                'language_components': [],
                'action_components': []
            }
            
            # 모델 상태 딕셔너리 분석
            if 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
                info['model_state_dict_keys'] = list(state_dict.keys())
                info['parameter_count'] = sum(p.numel() for p in state_dict.values())
                
                # 컴포넌트별 분석
                for key in state_dict.keys():
                    key_lower = key.lower()
                    
                    # Kosmos2 관련
                    if any(x in key_lower for x in ['kosmos', 'text', 'language']):
                        info['kosmos2_components'].append(key)
                    
                    # CLIP 관련
                    if any(x in key_lower for x in ['clip', 'vision', 'image']):
                        info['clip_components'].append(key)
                    
                    # LSTM 관련
                    if any(x in key_lower for x in ['lstm', 'rnn', 'recurrent']):
                        info['lstm_components'].append(key)
                    
                    # Vision 관련
                    if any(x in key_lower for x in ['conv', 'resnet', 'backbone', 'encoder']):
                        info['vision_components'].append(key)
                    
                    # Language 관련
                    if any(x in key_lower for x in ['embedding', 'transformer', 'attention']):
                        info['language_components'].append(key)
                    
                    # Action 관련
                    if any(x in key_lower for x in ['action', 'output', 'head', 'predictor']):
                        info['action_components'].append(key)
                
                # 모델 타입 판별
                if len(info['clip_components']) > 0 and len(info['kosmos2_components']) > 0:
                    info['model_type'] = 'Kosmos2 + CLIP Hybrid'
                elif len(info['kosmos2_components']) > 0:
                    info['model_type'] = 'Pure Kosmos2'
                elif len(info['clip_components']) > 0:
                    info['model_type'] = 'Pure CLIP'
                else:
                    info['model_type'] = 'Custom Architecture'
                
                # 아키텍처 컴포넌트 정리
                if info['vision_components']:
                    info['architecture_components'].append('Vision Encoder')
                if info['language_components']:
                    info['architecture_components'].append('Language Model')
                if info['lstm_components']:
                    info['architecture_components'].append('LSTM Layer')
                if info['action_components']:
                    info['architecture_components'].append('Action Predictor')
            
            # 추가 정보
            if 'val_mae' in checkpoint:
                info['val_mae'] = checkpoint['val_mae']
            if 'epoch' in checkpoint:
                info['epoch'] = checkpoint['epoch']
            
            return info
            
        except Exception as e:
            print(f"❌ Error analyzing checkpoint: {e}")
            return {'error': str(e)}
    
    def compare_architectures(self, checkpoints: List[str]) -> Dict[str, Any]:
        """여러 체크포인트 비교"""
        print(f"\n🔍 Comparing {len(checkpoints)} architectures")
        print("=" * 80)
        
        results = {}
        for checkpoint_path in checkpoints:
            if os.path.exists(checkpoint_path):
                model_name = os.path.basename(checkpoint_path).replace('.pth', '')
                results[model_name] = self.analyze_checkpoint_structure(checkpoint_path)
            else:
                print(f"❌ Checkpoint not found: {checkpoint_path}")
        
        return results
    
    def explain_differences(self, results: Dict[str, Any]):
        """아키텍처 차이점 설명"""
        print(f"\n📚 Architecture Differences Explanation")
        print("=" * 80)
        
        # VLM vs RoboVLMs vs LSTM 설명
        print(f"\n🎯 **VLM (Vision-Language Model) vs RoboVLMs vs LSTM Layer**")
        print("-" * 60)
        
        print(f"\n🔍 **VLM (Vision-Language Model)**:")
        print("   - Vision과 Language를 결합한 모델")
        print("   - 이미지와 텍스트를 동시에 처리")
        print("   - 예: CLIP, Kosmos2, Flamingo")
        print("   - 특징: 멀티모달 이해, 시각적 추론")
        
        print(f"\n🤖 **RoboVLMs (Robot Vision-Language Models)**:")
        print("   - 로봇 제어에 특화된 VLM")
        print("   - Vision + Language → Action 매핑")
        print("   - 로봇 동작 명령 생성")
        print("   - 특징: 실시간 제어, 안전성, 정확성")
        
        print(f"\n🧠 **LSTM Layer**:")
        print("   - 순환 신경망의 한 종류")
        print("   - 시퀀스 데이터 처리")
        print("   - 장기 의존성 학습")
        print("   - 특징: 시계열 예측, 메모리 유지")
        
        # 실제 모델 분석
        print(f"\n📊 **실제 모델 분석 결과**:")
        print("-" * 60)
        
        for model_name, info in results.items():
            if 'error' not in info:
                print(f"\n🏷️  **{model_name}**:")
                print(f"   - 모델 타입: {info['model_type']}")
                print(f"   - 파일 크기: {info['file_size_mb']:.1f}MB")
                print(f"   - 파라미터 수: {info['parameter_count']:,}")
                print(f"   - 아키텍처: {', '.join(info['architecture_components'])}")
                
                if 'val_mae' in info:
                    print(f"   - 검증 MAE: {info['val_mae']:.4f}")
                if 'epoch' in info:
                    print(f"   - 훈련 에포크: {info['epoch']}")
                
                # 컴포넌트별 상세 분석
                if info['vision_components']:
                    print(f"   - Vision 컴포넌트: {len(info['vision_components'])}개")
                if info['language_components']:
                    print(f"   - Language 컴포넌트: {len(info['language_components'])}개")
                if info['lstm_components']:
                    print(f"   - LSTM 컴포넌트: {len(info['lstm_components'])}개")
                if info['action_components']:
                    print(f"   - Action 컴포넌트: {len(info['action_components'])}개")
    
    def create_architecture_summary(self, results: Dict[str, Any]):
        """아키텍처 요약 생성"""
        print(f"\n📋 Architecture Summary")
        print("=" * 80)
        
        summary = {
            'total_models': len(results),
            'model_types': {},
            'file_sizes': {},
            'parameter_counts': {},
            'architectures': {}
        }
        
        for model_name, info in results.items():
            if 'error' not in info:
                # 모델 타입별 분류
                model_type = info['model_type']
                if model_type not in summary['model_types']:
                    summary['model_types'][model_type] = []
                summary['model_types'][model_type].append(model_name)
                
                # 파일 크기
                summary['file_sizes'][model_name] = info['file_size_mb']
                
                # 파라미터 수
                summary['parameter_counts'][model_name] = info['parameter_count']
                
                # 아키텍처
                summary['architectures'][model_name] = info['architecture_components']
        
        # 요약 출력
        print(f"\n📊 **모델 분류**:")
        for model_type, models in summary['model_types'].items():
            print(f"   - {model_type}: {len(models)}개 모델")
            for model in models:
                print(f"     * {model}")
        
        print(f"\n📏 **파일 크기 비교**:")
        for model_name, size in summary['file_sizes'].items():
            print(f"   - {model_name}: {size:.1f}MB")
        
        print(f"\n🧮 **파라미터 수 비교**:")
        for model_name, params in summary['parameter_counts'].items():
            print(f"   - {model_name}: {params:,} 파라미터")
        
        print(f"\n🏗️  **아키텍처 구성**:")
        for model_name, components in summary['architectures'].items():
            print(f"   - {model_name}: {', '.join(components)}")
        
        return summary

def main():
    """메인 함수"""
    print("🚀 Starting Model Architecture Analysis")
    print("🎯 Analyzing VLM, RoboVLMs, and LSTM differences")
    
    analyzer = ModelArchitectureAnalyzer()
    
    # 분석할 체크포인트들
    checkpoints = [
        "Mobile_VLA/results/simple_clip_lstm_results_extended/best_simple_clip_lstm_model.pth",
        "Mobile_VLA/results/simple_lstm_results_extended/best_simple_lstm_model.pth",
        "Mobile_VLA/results/simple_lstm_results_extended/final_simple_lstm_model.pth"
    ]
    
    try:
        # 체크포인트 분석
        results = analyzer.compare_architectures(checkpoints)
        
        # 차이점 설명
        analyzer.explain_differences(results)
        
        # 요약 생성
        summary = analyzer.create_architecture_summary(results)
        
        # 결과 저장
        output_path = "Mobile_VLA/architecture_analysis_results.json"
        with open(output_path, "w") as f:
            json.dump({
                'analysis_results': results,
                'summary': summary,
                'timestamp': '2024-08-22'
            }, f, indent=2)
        
        print(f"\n✅ Analysis completed! Results saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        raise

if __name__ == "__main__":
    main()
