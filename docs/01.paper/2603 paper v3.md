
Enhancing Generalization in Mobile Navigation: Adapting RoboVLMs for Complex Instruction Following in Memory-Constrained Embedded Systems  
Min-Woo Lee*,  In-Yeop Choi**

[Abstract]
This paper proposes the results of optimizing and implementing the RoboVLMs framework for a mobile robot navigation environment to overcome the limitations of existing Vision-Language-Action (VLA) models. While existing VLA-based navigation models demonstrate powerful visual understanding, they suffer from high inference costs due to their interleaved architecture, reduced control precision due to discrete action prediction, and their large model size, making them unsuitable for deployment on memory-constrained mobile devices. Lightweight models such as TIC-VLA and OmniVLA-edge often suffer from reduced understanding of complex language commands during model size reduction and poor generalization performance in out-of-distribution environments. In this study, we demonstrate that RoboVLMs leverages its powerful vision-language backbone and efficient policy head architecture to support high-level contextual understanding and continuous action spaces, enabling precise and intelligent navigation of 2-DoF mobile robots even on the NVIDIA Jetson Orin NX, a 16GB memory-constrained system.
▸Key words: RoboVLMs, VLA, VLM, 
[요   약]
본 연구는 기존의 Vision-Language-Action (VLA) 모델이 가진 한계를 극복하기 위해, RoboVLMs 프레임워크를 모바일 로봇 내비게이션 환경에 맞춰 최적화 및 구현한 결과를 제시한다. 기존의 VLA 기반 내비게이션 모델들은 강력한 시각 이해력을 보여주지만, Interleaved 구조로 인한 높은 추론 비용과 이산적 액션 예측으로 인한 제어 정밀도 저하되고, 모델 크기가 커서 메모리 제약적인 모바일 기기에 탑재하지 못하는 한계가 있다. TIC-VLA와 OmniVLA-edge 같은 경량화 모델인 경우 모델 크기를 줄이는 과정에서 복잡한 언어 명령 이해 능력이 저하되거나, 학습 분포를 벗어난 환경에서의 일반화 성능이 낮은 문제를 지니고 있다. 본 연구에서는 RoboVLMs의 강력한 시각-언어 백본과 효율적인 정책 헤드(Policy Head) 구조를 활용하여, 16GB의 메모리 제한이 있는 NVIDIA Jetson Orin NX 환경에서도 고수준의 문맥 이해와 연속적 액션 공간을 지원하여 2-DoF 모바일 로봇의 정밀하고 지능적인 주행을 가능케 함을 입증하였다. 


▸주제어: RoboVLMs, VLA, VLM, 모바일 VLA, 실시간 내비게이션, 하이브리드 아키텍처, Kosmos-2, CLIP, LSTM 정책 헤드, LoRA fine-tuning
I. Introduction
  Vision-Language-Action (VLA) 모델은 딥러닝 연구가 단순한 "시각 인식"과 "언어 인식"을 넘어서 물리적 로봇에게 적용하여 언어 지시를 이해하고 시각을 통한 상황을 인지한 후에 실제 로봇 행동으로 연결하기 위해 등장했다. "컵을 집어줘"라는 언어 정보를 이해한 후에 카메라 이미지와 영상 같은 시각 정보로 상황을 인지한 후에 로봇 팔의 회전, 경로, 그리퍼 동작 같은 실행해야 할 실제 동작 시퀀스의 액션을 직접 학습하는 모델이다.
  이러한 연구가 필요하게 된 이유는 전통적인 로봇 구조의 한계에 있다. 기존에 로봇들이 공장에서 프로그래밍된 대로 반복 작업을 하였다. 그러나 서비스 로봇들은 이러한 로봇에게 언어로 지시하면 이를 알아듣고, 현재 상황을 인지하여 명령을 자연스럽게 처리해야 한다. 서비스는 특정 작업만 하는 것이 아니라 다양한 상황에 적용 가능한 범용성이 필요하다.

1. SLAM의 한계와 VLA의 등장 

  전통적인 로봇 내비게이션은 SLAM을 통한 지도 생성과 경로 최적화에 의존해 왔다. 그러나 이러한 방식은 환경의 기하학적 정보에만 치중하여, "간식이 있는 곳으로 이동해"와 같은 인간의 시맨틱(Semantic)한 명령을 처리하는 데 한계가 있다. 이를 해결하기 위해 등장한 VLA 모델은 대규모 멀티모달 학습을 통해 시각 정보와 언어 명령을 직접 로봇의 행동(Action)으로 연결하며 로봇 지능의 새로운 지평을 열었다.

2. 기존 모바일 VLA 모델의 한계점

대표적인 모바일 VLA 모델은 NaVid와 NaVILA 이다. 이 모델들은 비전 관찰을 직접적인 로봇 동작으로 연결하는 대규모 모델에 가깝다. 특히 NaVid는 비디오 확산(Diffusion) 모델이나 대규모 사전 학습된 VLM을 기반으로 하여 내비게이션 태스크를 수행한다. 그러나 이 모델들은 구조적, 기능적 한계가 있다. NaVid 모델은 비전 토큰과 행동 토큰을 단순히 나열하여 처리하는 Interleaved 방식을 사용한다. 이는 모델이 과거의 맥락(Context)을 이해하기 위해 매 단계마다 막대한 양의 토큰을 다시 계산해야 한다. 그러므로 실시간성이 중요한 모바일 로봇 내비게이션에서 연산 비효율을 초래한다. NaVILA 모델은 행동을 텍스트처럼 이산화된 토큰으로 예측한다. 이는 2-DoF 모바일 로봇이 매끄럽게 가속하거나 미세한 각도로 회전해야 하는 연속적(Continuous) 제어 상황에서 성능 저하나 불연속적인 움직임을 유발할 수 있다. 또한 이 모델들은 비전 관찰을 직접적인 로봇 동작으로 연결함으로 시각적 명사 이해에는 강하다. 하지만 "장애물을 피해 돌아가서 문 뒤의 물체를 확인해"와 같은 복잡한 장기 계획(Long-horizon)이나 다단계 추론에서 실패할 확률이 높다. 결정적으로 모델의 크기가 커서 모바일 로봇에 적용하기가 어렵다.   
최근 모바일 로봇의 실시간성을 확보하기 위해 모바일 디바이스에 탑재하기 용이한  TIC-VLA 와 OmniVLA- edge 같은 경량 VLA 모델도 있다. 하지만 이러한 모델들은 임베디드 환경에 맞추기 위해 파라미터 수를 극단적으로 줄이면서 성능적 결함을 가지고 있다. 첫째는 언어 이해의 경직성이다. 이들은 주로 단순한 템플릿 기반 명령에만 반응하여 복잡한 문맥을 파악하지 못한다. 둘째는 낮은 일반화 성능이다. 학습 데이터와 조금이라도 다른 새로운 환경(Unseen environment)에서는 주행 능력이 현저하게  떨어진다. 셋째는 추론 능력의 부족이다. 장기적인 계획(Long-horizon planning)이나 다단계 논리 추론이 불가능하여 복잡한 임무 수행에 부적합하다. 
기존에 제안된 모바일 VLA 모델의 이러한 한계점을 보완하기 위해 VLA 모델로 RoboVLMs를 선택하여 메모리가 제한된 모바일 로봇에 탑재하였다.  

3. RoboVLMs를 선택한 이유

RoboVLMs을 선택한 첫번째 이유는 모델 용량이다. 메모리 제한적인 로봇에 탑재하기 위해서 모델 크기는 가장 중요한 선택 이유이다. 현재 성능이 좋은 VLA 모델은 많이 있다. 하지만 성능이 좋은 대부분의 VLA 모델은 사이즈가 커서 메모리가 16Gb를 가진 모바일 로봇에서 작동하지 못한다. RoboVLMs는 상대적으로 모델 사이즈가 작아서 메모리 제한적인 로봇에 탑재할 수 있다. 두 번째 이유는 다른 모델에 비해 기술적 우위이다. RoboVLMs가 가진 기술적 우위는 다음과 같다. 첫째, Policy Head 기반의 효율적인 통합이다. RoboVLMs은 VLM의 강력한 표현력(Representation)은 그대로 유지하면서, 별도의 Policy Head를 통해 과거 이력 정보를 통합한다. 이 구조는 VLM 백본의 언어 이해 능력을 해치지 않으면서도 로봇의 2-DoF 제어에 필요한 핵심 정보만을 효율적으로 추출할 수 있게 해준다. 둘째, 연속적인 액션 공간을 지원한다. RoboVLMs는 연속적인 액션 공간을 직접 출력할 수 있도록 설계되어 있다. 이는 바퀴 기반 로봇의 선속도와 각속도를 정밀하고 부드럽게 제어하는 데 있어 이산화 방식보다 훨씬 유리하다. 셋째, 높은 일반화 및 제로샷(Zero-shot) 성능 때문이다. RoboVLMs는 KosMos나 PaliGemma와 같은 강력한 VLM 백본을 사용하여, 학습 데이터에 없던 새로운 물체나 환경(Unseen Scenes)에서도 탁월한 적응력을 보여준다. 넷째, 유연한 프레임워크 설계이다. RoboVLMs는 다양한 VLM 백본을 쉽게 교체하고 통합할 수 있는 오픈소스 프레임워크를 제공한다. 


4. VLM 백본 선택 

 본 연구에서는 VLM 백본으로 Microsoft Kosmos-2 Vision-Language 모델을 선택하였다. Kosmos-2는 멀티모달 대형 언어 모델로서, 시각적 세계와의 텍스트 연결을 강화하여 다양한 다운스트림 작업에서 우수한 성능을 발휘한다. Kosmos-2는 기존 VLM들이 단순히 이미지와 텍스트를 분리하여 처리하는 것과 달리, 시각적 세계와 텍스트를 통합적으로 이해하는 능력을 갖추고 있다.
  Kosmos-2 선택의 결정적 요인은 다음과 같다. 첫째, 학술적 검증이다. 선행연구의 8가지 VLM 백본 비교에서 최고 성능을 달성하였다. 둘째, 멀티모달 통합이다. 시각과 언어의 통합적 이해 능력을 제공한다. 셋째, 로봇 제어 적합성이다. 언어 조건부 조작 작업에 최적화된 아키텍처를 가지고 있다. 넷째, 확장성이다. 다양한 다운스트림 태스크에 대한 우수한 일반화 능력을 제공한다. 다섯째, 실용성이다. 실제 로봇 환경에서의 안정적인 성능을 보장한다.


II. Preliminaries
1. Related works

1.1 RoboVLMs 아키텍처 분석
RoboVLMs는 기존의 Generalist Policies와 최근 연구들을 분류 체계에 따라 정리한 프레임워크이다. 이 분류는 액션 공간(연속적/이산적)과 히스토리 정보 통합 방식(원스텝/히스토리컬)을 기준으로 한다. 원스텝 방식은 현재 상태만을 사용하여 액션을 예측하고, 히스토리컬 방식은 과거 정보를 포함하는 슬라이딩 윈도우를 처리한다. 히스토리컬 방식은 다시 Policy-Head와 Interleaved로 나뉜다. Policy-Head는 히스토리 정보가 별도의 정책 헤드를 통해 처리되고, Interleaved는 히스토리컬 관찰과 액션 시퀀스가 교차된 형식으로 통합된다.

  RoboVLMs는 4가지 주요 아키텍처 패러다임을 제시한다. 
첫째, One-Step-Continuous-Action Models는 현재 상태만을 사용하여 연속 액션을 한 단계에서 생성한다. 
둘째, Interleaved-Continuous-Action Models는 연속 액션을 교차 방식으로 생성하며 역사적 컨텍스트를 포함한다. 
셋째, One-Step-Discrete-Action Models는 이산 액션을 한 단계에서 생성한다. 
넷째, Policy-Head-Continuous-Action Models는 별도의 Policy Head를 사용하여 연속 액션을 생성한다.

본 연구에서 제안하는 Mobile VLA 시스템은 Policy-Head-Continuous-Action Models 패러다임에 해당하며, Kosmos-2 + CLIP 하이브리드 VLM을 사용하여 시각-언어 특징을 추출하고, LSTM 기반의 정책 헤드로 2D 연속 액션을 생성한다. 이 구조는 모바일 환경에 최적화되어 실시간 로봇 제어가 가능하다. 기존 RoboVLMs의 7-DoF 로봇 팔 제어를 2-DoF 모바일 로봇 내비게이션에 적용한 것이 우리 연구의 핵심이다.


1.2 OpenVLA
  OpenVLA는 오픈소스 Vision-Language-Action 모델로, 다양한 로봇 제어 태스크에서 우수한 성능을 보인다. OpenVLA는 CLIP 기반의 VLM을 사용하여 시각-언어 이해 능력을 제공하고, 이를 로봇 제어에 적용한다. OpenVLA의 주요 특징은 모듈화된 아키텍처와 확장 가능한 설계이다.
1.3 π0 (Pi-0)
π0는 Google DeepMind에서 개발한Vision-Language-Action 모델로, 로봇 제어를 위한 특화된 아키텍처를 제공한다. π0는 시각-언어 모델을 기반으로 하여 로봇 액션을 직접 생성하는 end-to-end 방식을 채택한다. π0의 주요 기여는 로봇 제어를 위한 특화된 학습 방법론과 아키텍처 설계이다.
1.4 SayCan
  SayCan은 Google에서 개발한 로봇 제어 시스템으로, 언어 모델을 사용하여 로봇 액션을 계획하고 실행한다. SayCan은 언어 모델의 추론 능력을 활용하여 복잡한 로봇 태스크를 단계별로 분해하고 실행한다. SayCan의 주요 특징은 언어 기반의 계획 수립과 실행 능력이다.
1.5 RT-2
  RT-2는 Google DeepMind에서 개발한 Vision-Language-Action 모델로, 로봇 제어를 위한 특화된 아키텍처를 제공한다. RT-2는 시각-언어 모델을 기반으로 하여 로봇 액션을 직접 생성하는 방식을 채택한다. RT-2의 주요 기여는 로봇 제어를 위한 특화된 학습 방법론과 아키텍처 설계이다.
1.6 PaLM-E
  PaLM-E는 Google에서 개발한 멀티모달 언어 모델로, 시각, 언어, 로봇 제어를 통합적으로 처리한다. PaLM-E는 PaLM 언어 모델을 기반으로 하여 시각 정보와 로봇 액션을 통합적으로 처리한다. PaLM-E의 주요 특징은 대규모 언어 모델의 추론 능력을 로봇 제어에 적용한 것이다.
2. VLA 모델 분류
VLA 모델은 크게 두 가지 접근 방식으로 분류할 수 있다. 첫째, 모듈화된 접근 방식이다. 이 방식에서는 시각 처리, 언어 처리, 액션 생성을 각각 독립적인 모듈로 구성한다. 이 방식의 장점은 각 모듈을 독립적으로 최적화할 수 있다는 것이지만, 모듈 간의 통합이 어려울 수 있다.
둘째, 통합된 접근 방식이다. 이 방식에서는 시각, 언어, 액션을 하나의 통합된 모델에서 처리한다. 이 방식의 장점은 모듈 간의 통합이 용이하고 end-to-end 최적화가 가능하다는 것이지만, 모델의 복잡성이 증가할 수 있다.
3. 연구 간극 및 기여

기존 VLA 모델들은 주로 고성능 컴퓨팅 환경에서의 실험에 집중하였다. 이러한 모델들은 우수한 성능을 보이지만, 모바일 환경이나 엣지 디바이스에서의 실시간 처리는 어려움이 있다. 또한, 기존 모델들은 주로 로봇팔 제어에 집중하여 모바일 로봇 내비게이션에는 직접적으로 적용하기 어려운 경우가 많다.
본 연구의 주요 기여는 모바일 환경에 최적화된 VLA 모델을 개발한 것이다. 구체적으로는 Jetson Orin NX와 같은 엣지 디바이스에서 실시간 동작 가능한 VLA 모델을 구현하였고, 모바일 로봇 내비게이션에 특화된 2D 액션 공간을 사용하여 성능을 최적화하였다. 또한, Kosmos-2와 CLIP을 효과적으로 조합한 하이브리드 아키텍처를 제안하여 성능을 향상시켰다.
 III. The Proposed Scheme 

3.1. RoboVLMs 분석

  이 논문은 Vision-Language-Action 모델(VLA)을 기반으로 한 범용 로봇 정책(generalist robot policies) 구축에 필요한 핵심 요소들을 체계적으로 분석하고, 새로운 프레임워크인 RoboVLMs를 제안한다. 연구는 VLA 아키텍처를 구성하는 방법에 대한 세 가지 필수적인 설계 선택에 중점을 두었다. VLM 백본 선택, VLA 아키텍처 구성 그리고 교차-구현 데이터 추가 시점이다. Kosmos-2 기반으로 기존 Vision-Language Model을 로봇 제어용으로 확장한 end-to-end 학습 프레임워크이다. 언어 명령을 받고 이미지 관찰후에 즉시 로봇 액션을 생성하는 실용적인 실시간 로봇 제어를 보여준다.

본 연구에서는 RoboVLMs의 4가지 아키텍처 패러다임 중 Policy-Head-Continuous-Action Models를 선택하였다. 이 선택의 이유는 다음과 같다. 첫째, 모바일 환경에서의 실시간 처리 요구사항을 만족하기 위해 별도의 Policy Head를 사용하여 효율적인 액션 생성을 가능하게 한다. 둘째, 연속적인 액션 공간을 사용하여 모바일 로봇의 부드러운 내비게이션을 보장한다. 셋째, LSTM 기반의 Policy Head를 통해 시간적 정보를 효과적으로 처리할 수 있다.

3.1.1 RoboVLMs 프레임워크

다양한 VLM 백본과 VLA 구조를 쉽게 통합할 수 있는 유연하고 개방형(open-source) 프레임워크이다. 시뮬레이션(CALVIN, SimplerEnv)과 실제 로봇 실험에서 최신 성능(state-of-the-art)을 달성하였다.
RoboVLMs는 4가지 주요 아키텍처 패러다임을 제시한다. 첫째, One-Step-Continuous-Action Models이다. 이 패러다임에서는 VLM이 토큰 시퀀스를 받아 단일 연속 액션을 한 단계에서 생성한다. Text Tokens와 Vision Tokens를 입력받아 단일 Current token을 출력하고, 이를 Action Decoder로 전달하여 Current action을 생성한다.
둘째, Interleaved-Continuous-Action Models이다. 이 패러다임에서는 연속 액션을 교차 방식으로 생성하며, 역사적 컨텍스트를 포함한다. VLM이 교차된 토큰의 긴 시퀀스를 받아 History tokens와 Current token을 출력하고, 이를 Action Decoder로 전달하여 History token 입력과 함께 Current action을 생성한다.
셋째, One-Step-Discrete-Action Models이다. 이 패러다임에서는 이산 액션을 한 단계에서 생성한다. Text Tokens와 Vision Tokens를 입력받아 Discrete tokens 시퀀스를 출력하고, 이를 Detokenizer & Reprojection 모듈로 전달하여 Discrete actions 시퀀스를 생성한다.
넷째, Policy-Head-Continuous-Action Models이다. 이 패러다임에서는 별도의 Policy Head를 사용하여 연속 액션을 생성한다. Text Tokens와 Vision Tokens를 입력받아 단일 Current token을 출력하고, 이를 Policy Head로 전달하여 History tokens와 Current action을 생성한다.
본 연구에서 제안하는 Mobile VLA 시스템은 Policy-Head-Continuous-Action Models 패러다임을 따른다. 이는 Kosmos-2 + CLIP 하이브리드 VLM을 사용하여 시각-언어 특징을 추출하고, LSTM 기반의 Policy Head(4층, 1024 hidden size)를 통해 2D 연속 액션 [linear_x, linear_y]을 생성하는 구조이다.


3.1.2 VLA 아키텍쳐 구성 
본 연구에서는 Kosmos-2 VLM을 기반으로 하여 액션 예측 기능을 추가하였다. 훈련 데이터는 직접 수집한 모바일 로봇 내비게이션 데이터셋을 사용하였으며, 정책 헤드를 LSTM 기반으로 2DoF 모바일 로봇을 제어하였다.

3.1.2.1 정책의 기본 개념 
정책(Policy)은 강화학습과 로봇공학에서 나온 개념으로, "주어진 상황에서 어떤 행동을 할지 결정하는 규칙 또는 함수"를 의미한다. 언어 명령과 이미지를 보고 로봇 액션으로 변환한다. 이미지와 언어 입력이 주어졌을 때, 로봇 액션을 선택하는 함수는 다음과 같다. 
  π(action | vision, language, history)


  
3.1.2.2 VLA에서 정책의 역할 

VLA 시스템에서 정책은 다음과 같은 역할을 한다. 


RoboVLMs에서는 4가지 정책 헤드로 구현되었다. 첫째는 즉시 반응형 정책인 FCDecoder로 직관적이고 빠른 특징이 있다. 단순한 집기나 놓기 등에 사용된다. 두 번째는 시간 순서가 중요한 순차적 정책인 LSTMDecoder로 연속적인 조작이 중요한 상황에서 사용된다. 세 번째는 어텐션 메커니즘을 사용한 GPTDecoder로 강력한 추론이 가능하여 복잡한 멀티태스크 상황에 적합하다. 네 번째는 언어와 액션이 통합된 DiscreteDecoder로 언어와 밀접한 태스크를 수행하는 상황에 적합하다.

3.1.2.3 RoboVLMs 실행 플로우
RoboVLMs는 6-DOF 팔 + 1-DOF 그리퍼를 제어하는 7-DOF 제어 시스템이다. 비전, 언어, 액션 히스토리, 로봇 상태 융합하여 멀티모달 통합하였다. window-chunk 방식의 과거로 미래를 예측하였다. 액션 예측, 미래 관찰, 캡션 생성 동시 최적화하는 멀티태스크 학습을 수행한다. 본 연구에서는 이를 2-DOF 모바일 로봇 내비게이션에 적용하였다.

3.1.2.4 시간적 구조화
윈도우-청크 분할을 통해 과거 8프레임 관찰하여, 미래 10프레임을 예측한다. 과거는 미래 예측에만 허용되고, 미래는 과거의 정보 유출을 차단한다.
시간 순서별 동작 시뮬레이션은 아래와 같다.



3.1.2.5 RoboVLM 학습 
본 연구에서는 Kosmos-2 VLM을 기반으로 하여 액션 예측 기능을 추가하였다. 훈련 데이터는 직접 수집한 모바일 로봇 내비게이션 데이터셋(V2, V3)을 사용하였으며, 정책 헤드를 LSTM 기반으로 구성하여 2-DoF 모바일 로봇을 제어하였다. 

학습 과정에서의 핵심 전략은 **LoRA (Low-Rank Adaptation)** 기법의 활용이다. 거대한 VLM 백본(Kosmos-2)의 전체 파라미터(약 1.6B)를 모두 업데이트하는 대신, Query, Value, Key 프로젝션 레이어에 Rank 32, Alpha 64 설정의 LoRA 어댑터를 삽입하였다. 이를 통해 하드웨어의 시각적 특징 추출 능력을 내비게이션 도메인에 맞게 미세 조정(Fine-tuning)하면서도, 학습 파라미터 수를 1% 미만으로 유지하여 효율적인 학습을 달성하였다.

또한 시간적 선후 관계를 학습하기 위해 윈도우 크기 8의 시퀀스 데이터를 활용하였으며, 4층 구조의 LSTM(Hidden Size 1024) 정책 헤드를 통해 복잡한 주행 패턴을 학습하였다. 학습에는 AdamW 옵티마이저(LR 1e-5)를 사용하였으며, 과적합 방지를 위해 Early Stopping 기법을 적용하여 약 10-15 에포크 동안 진행되었다.

1.4 모바일 로봇에 탑재 
학습된 VLA 모델은 **FastAPI 기반의 Inference Server**와 **ROS 2 Client** 구조로 모바일 로봇(Serbot)에 탑재되었다.

Jetson Orin NX(16GB) 환경에서의 실행 최적화를 위해 다음과 같은 과정을 거쳤다:
1.  **Inference Server 구현**: Python FastAPI를 사용하여 모델 추론 서버를 구축하였다. 모델 로딩 시 `BitsAndBytes` 라이브러리를 통한 INT8 양자화 또는 FP16/BF16 정밀도를 선택 가능하게 하여 메모리 효율성을 극대화하였다. (INT8 사용 시 약 7.4GB VRAM 점유)
2.  **ROS 2 클라이언트 노드 개발**: `vla_api_client.py` 및 ROS 2 전용 노드를 통해 로봇의 카메라 이미지를 서버로 전송하고, 서버에서 계산된 [linear_x, angular_z] 액션을 받아 `Twist` 메시지로 로봇 가동부에 명령을 하달한다.
3.  **비동기 추론 루프**: 로봇의 실시간 제어 주기를 보장하기 위해 추론 루프와 키보드 입력 인터럽트, ROS 메시지 통신을 각각 별도의 스레드(MultiThreadedExecutor)에서 처리하여 Deadlock을 방지하고 약 10Hz 수준의 추론 속도를 확보하였다.

1.5 다른 VLA와의 차이점 
본 연구의 주요 차이점은 다음과 같다. 첫 번째는 모바일 주행 환경에 최적화된 **2D 액션 공간** 재설계이다. 기존 RoboVLMs의 7-DoF 매니퓰레이션 액션을 선속도와 각속도로 단순화하여 학습 효율을 높였다. 두 번째는 **Kosmos-2와 CLIP의 하이브리드 아키텍처** 활용이다. 강력한 VLM 백본의 시맨틱 이해 능력과 CLIP의 정밀한 시각 특징을 결합하여 목표물인 그레이 바스켓 인식 성능을 강화하였다. 세 번째는 **임베디드 타겟 최적화**이다. 수십 GB를 요구하는 일반 VLA와 달리 16GB 이하의 엣지 디바이스에서 구동 가능한 경량 추론 파이프라인을 구축하였다.

2. RoboVLMs 한계점

2.1 멀티모달 상호작용 구조의 제한
기존 VLM의 구조(예: attention mask, mixture of experts)를 그대로 유지한 채 VLA를 구성했기 때문에, 행동(action)과의 상호작용을 위한 전용 아키텍처 설계가 부족하다. π0 같은 모델은 이러한 상호작용을 더 정교하게 설계하여 성능 향상을 보여주므로, 향후 연구에서 구조적 개선이 필요하다.

2.2 VLA 구조의 단순화
논문에서 고려한 VLA 구조는 네 가지로 제한되어 있으며, 다양한 구조적 변형이나 세부 설계 요소(예: attention 방식, token 처리 방식 등)에 대한 탐색이 부족하다. 

2.3 행동 토크나이징 및 학습 목표의 미탐색
행동을 표현하는 방식(예: VQ-VAE, diffusion models, flow matching 등)에 대한 실험이 부족하며, 정교한 행동 표현 및 예측 방식에 대한 연구가 향후 필요하다.

3. RoboVLMs 개선 제안 

RoboVLMs의 한계점을 보완하기 위해 다음과 같은 개선 방안을 실제 시스템에 반영하였다.

3.1 아키텍처 개선 방안

3.1.1 멀티모달 상호작용 강화
기존 RoboVLMs의 VLM 구조를 그대로 유지하는 방식에서 벗어나, 행동(action)과의 상호작용을 위한 전용 아키텍처를 설계한다. π0 모델에서 보여준 것처럼, 시각-언어-행동 간의 더 정교한 상호작용 메커니즘을 도입하여 성능을 향상시킨다.

3.1.2 VLA 구조 다양화
4가지 패러다임에 국한되지 않고, 다양한 구조적 변형을 탐색한다. Attention 방식의 개선, Token 처리 방식의 최적화, 그리고 새로운 융합 기법을 도입하여 더 유연하고 효율적인 VLA 구조를 제안한다.
3.1.3 행동 표현 방식 혁신
VQ-VAE, Diffusion Models, Flow Matching 등 다양한 행동 표현 방식을 실험적으로 검증하고, 정교한 행동 표현 및 예측 방식에 대한 새로운 접근법을 제시한다.
3.2 모바일 환경 최적화 전략
3.2.1 모바일 특화 아키텍처
기존 RoboVLMs의 7-DoF 로봇 팔 제어 중심에서 벗어나, 2-DoF 모바일 로봇 내비게이션에 특화된 아키텍처를 설계한다. 모바일 환경의 제약사항(계산 자원, 배터리, 실시간성)을 고려한 최적화된 구조를 제안한다.
3.2.2 효율적인 멀티모달 융합
Kosmos-2와 CLIP의 하이브리드 아키텍처를 통해 시각-언어 특징을 효율적으로 융합한다. 4352차원의 통합 특징을 2048차원으로 압축하여 모바일 환경에서의 실시간 처리를 가능하게 한다.
3.2.3 LSTM 기반 시퀀스 처리
4층 LSTM을 사용하여 복잡한 시퀀스 패턴을 학습하고, 18프레임의 시간적 정보를 효과적으로 처리한다. 이를 통해 모바일 로봇의 연속적인 내비게이션 결정을 지원한다.
3.3 실시간 처리 최적화
3.3.1 양자화 기법 적용
FP16 양자화를 통해 모델 크기를 줄이고 추론 속도를 향상시킨다. 정확도 손실을 최소화하면서도 모바일 환경에서의 실용성을 확보한다.
3.3.2 메모리 효율성 개선
CLIP 기반 모델의 1.7GB 메모리 사용량을 기준으로, 복잡한 하이브리드 모델도 7.4GB 이하로 유지하여 모바일 환경에서 수용 가능한 수준을 달성한다.
IV. Experimental Results
1. 실험 환경 및 설정

본 연구의 모델 학습은 NVIDIA A5000 GPU 환경에서 수행되었으며, 실시간 추론 실험은 NVIDIA Jetson Orin NX 16GB 환경에서 수행되었다. A5000은 24GB GDDR6 메모리와 8192개의 CUDA 코어를 제공하여 대규모 모델 학습에 최적화되어 있다. Jetson Orin NX는 ARM Cortex-A78AE 8-core CPU와 NVIDIA Ampere 1024-core GPU를 탑재하고 있으며, 16GB LPDDR5 메모리와 64GB eMMC 저장공간을 제공한다. 소프트웨어 환경은 Ubuntu 22.04 LTS 운영체제, Python 3.10, PyTorch 2.0+, ROS2 Humble, CUDA 12.0로 구성되었다.

실험에 사용된 데이터셋은 초기에 구축된 528개 에피소드(basket_dataset_v2)와 최근 더욱 정밀하게 정제된 `mobile_vla_dataset_v3`를 결합하여 활용하였다. 특히 `mobile_vla_dataset_v3`는 단순한 주행 데이터를 넘어, 거리별(J: 1m, K: 2m) 정렬 주행과 복합 장애물 시나리오를 포함한다.

본 연구에서는 데이터셋 명칭인 **V3(Dataset)**와 실험 시나리오인 **V4(Scenario)**를 명확히 구분하여 학습의 복잡도를 관리하였다:
1.  **V3(Dataset)**: 다양한 주행 변형(Variant V1~V4)을 포함하는 종합 수집 프로젝트이다. 이는 코어 주행 데이터 외에도 장애물 거리별 회피 패턴(V1~V3)을 포함하여 데이터의 다양성을 확보한다.
2.  **V4(Scenario)**: 데이터셋 내의 특정 변형인 **'Target-Only (No-obstacle)'** 시나리오를 지칭한다. 이는 "장애물이 없을 때는 직진 명령(V4)을 수행하고, 있을 때는 지능적으로 회피(V1-V3)한다"는 복합적인 상황 인지 능력을 평가하기 위한 핵심 시나리오이다.

실제 테스트 태스크는 하단 카메라 뷰에 포착된 **그레이 바스켓(Gray Basket)**을 인식하여 정밀하게 접근하는 '목표 정렬 접근(Target Alignment Access)'이다. 특히 V4 시나리오에서는 **"Navigate directly to the gray basket"** 명령을 통해 모델이 불필요한 조향 진동 없이 목표물에 최단 거리로 접근하는지를 검증하였다.



2. 모델 구성 및 성능 비교

실험에서 사용된 모델은 Kosmos-2 백본에 2-DoF 액션 헤드를 결합한 구조이다. 기존 RoboVLMs 성능 비교 결과(CALVIN/SimplerEnv)를 바탕으로, 모바일 환경에 가장 적합한 Policy-Head 기반 연속 액션 모델을 실구현하였다.









5. 테스트 수행 

실제 테스트는 그레이 바스켓이 배치된 실내 복도 환경에서 수행되었다. 총 20회의 주행 테스트를 통해 장애물 회피(V1-V3)와 직진 주행(V4) 성능을 검증하였다.

6. 테스트 결과 및 정량적 분석

학습 결과, VLM 백본에 LoRA를 선택적으로 적용한 **V3-exp07** 모델은 검증 데이터셋에서 **97.9%의 최고 정확도(Accuracy)**를 기록하였으며, 프롬프트 엔지니어링을 강화한 **V3-exp08**에서는 오프라인 테스트 기준 **PM(Perfect Match) 100%**를 달성하였다.

| Experiment | Instruction Type | PM (Perfect Match) | DM (Direction Match) | Val Loss |
| :--- | :--- | :---: | :---: | :---: |
| V3-exp04 | Basic | 82.5% | 85.1% | 0.294 |
| V3-exp07 | Goal-Oriented | 97.9% | 98.4% | 0.053 |
| **V3-exp08** | **Goal-Centric** | **100.0%** | **100.0%** | **0.031** |

특히, 실환경 주행 테스트(Online Inference)에서 확인된 **미션 성공률(Mission Success Rate)**은 다음과 같다. 성공 기준은 "목표물 30cm 이내 도달 및 장애물 충돌 없음"으로 정의하였다.

| Scenario | Task Description | Attempts | Success | Success Rate |
| :--- | :--- | :---: | :---: | :---: |
| V1-V3 | Obstacle Avoidance | 10 | 8 | 80% |
| **V4** | **Target-Only (Direct)** | **10** | **10** | **100%** |
| **Total** | **Integrated Nav** | **20** | **18** | **90%** |

이러한 결과는 모델이 단순한 이미지 매칭을 넘어, "Navigate directly"와 "Navigate toward... center-goal" 간의 언어적 뉘앙스를 파악하여 주행 전략을 동적으로 변경하고 있음을 입증한다. 특히 V4 시나리오 도입을 통해 고질적인 'Causal Confusion(타이밍 암기 현상)'을 억제하고, 시각 정보에 기반한 실시간 반응형 제어를 실현하였다.

V. Conclusions
1. 연구 성과 요약






첫째, 모바일 환경에 최적화된 VLA 모델 구축 및 실시간성 검증에 성공하였다. NVIDIA Jetson Orin NX(16GB) 환경에서 실시간 동작 가능한 VLA 서버-클라이언트 아키텍처를 구현하여, 메모리 사용량 7.4GB 수준에서 동작하며 최고 97.9%의 검증 정확도를 달성하였다.

둘째, **V3 데이터셋과 V4 시나리오**의 통합 학습을 통해 상황 인지 주행 지능을 확보하였다. 장애물 유무와 명령의 종류("Navigate directly..." vs "Navigate around obstacles...")를 문맥적으로 파악하여, 장애물 회피와 고속 직진 목표 정렬 행동을 유연하게 전환할 수 있음을 입증하였다. 이를 통해 조향 진동 문제를 해결하고 목표물에 대한 정밀한 접근 성능을 확보하였다.

2. 주요 기여도
본 연구의 주요 기여는 다음과 같다. RoboVLMs는 시각-언어 토큰의 특징을 보존하면서도 이력 정보(History)를 효율적으로 통합하는 정책 헤드 구조를 통해, 경량 모델들이 놓친 '추론 능력'과 '일반화'를 동시에 확보한다. 특히, 본 논문에서는 다음과 같은 기여를 하였다. 
2.1 액션 공간을 재설계 하였다. 7-DoF 매니퓰레이션 중심의 RoboVLM을 2-DoF 모바일 로봇의 선속도 및 각속도 제어로 최적화하여 학습 효율을 높였다.
2.2 컴퓨터 리소스 제한 적인 로봇에 모델을 최적화하여 탑재하였다. RoboVLM의 강력한 성능을 유지하면서도 최적화를 통해 NVIDIA Jetson Orin NX(16GB) 환경에서 구동 가능하도록 구현하여, 실용적 배포 가능성을 입증하였다.
2.3 지능적 내비게이션을 검증 하였다. 단순 이동을 넘어, 복합적인 지시어 이해와 상황 판단이 필요한 환경에서 본 모델이 안정적인 임무 성공률을 보임을 실험적으로 증명하였다.


본 연구에서는 Policy-Head-Continuous-Action Models 패러다임을 선택하여 모바일 환경에 최적화된 VLA 시스템을 성공적으로 구축하였다.

3. 연구의 한계점
본 연구는 몇 가지 한계점을 가지고 있다. 첫째, 도메인 갭(Domain Gap) 문제이다. 학습 시 사용된 카메라의 색조 및 화각과 실운용 환경 간의 차이로 인해 일부 환경에서 성능 편차가 발생할 수 있다. 둘째, 2.5D 정보 활용의 부족이다. 현재 2D 이미지 기반의 내비게이션에 특화되어 있으나, 더 복잡한 공간 추론을 위해 깊이 정보를 결합한 액션 공간 확장이 필요할 수 있다. 셋째, 특정 하드웨어 환경이다. Jetson Orin NX 환경에서 검증되었으나, 더 낮은 사양의 엣지 디바이스 확장을 위한 추가 최적화가 필요하다.

4. 향후 연구 방향
향후 연구 방향은 다음과 같다. 첫째, 데이터셋 확장이다. 더 다양한 환경과 시나리오를 포함하는 대규모 데이터셋을 구축하여 모델의 일반화 성능을 향상시켜야 한다. 둘째, 복잡한 액션 공간 확장이다. 2D 액션 공간을 넘어서 더 복잡한 로봇 제어 태스크에 적용할 수 있는 아키텍처를 개발해야 한다. 셋째, 다양한 하드웨어 환경 검증이다. Jetson Orin NX 외에도 다양한 엣지 디바이스에서의 성능을 검증하여 범용성을 높여야 한다.

5. 실용적 의의

이 논문은 제한된 메모리(16GB) 내에서도 상용 VLM의 강력한 이해 능력을 유지하면서, Policy Head를 통해 모바일 로봇 주행에 필요한 정확한 연속 제어와 장기적인 판단 능력을 확보한 것에 의의가 있다. 


6. 최종 결론

현재 모바일 기반 VLA 모델들이 존재하지만, 본 연구에서 RoboVLMs 프레임워크를 선택하고 이를 2-DoF 주행에 맞게 수정한 이유는 두 가지 핵심적인 기술적 이점 때문이다.
첫째, 구조적 효율성과 성능의 균형이다. RoboVLMs 모델의 Policy Head 구조는 Interleaved 등과 같은 모델 구조보다 일반화 성능과 데이터 효율성 면에서 우수함이 입증되었다.  본 연구는 Policy Head 구조를 유지하면서도 7-DoF의 복잡한 액션 공간을 2-DoF로 단순화하여 학습 효율을 극대화하였다.
둘째, 임베디드 하드웨어 호환성이다. 대부분의 고성능 VLA 모델은 수십 GB의 비디오 메모리(VRAM)를 요구하여 실제 이동 로봇에 탑재하기 불가능하다. 반면 RoboVLMs는 다양한 VLM 백본(PaliGemma 등)과의 결합이 자유로워, 16GB 메모리를 가진 Jetson Orin NX에서도 실시간 추론이 가능한 수준으로 모델 크기를 최적화할 수 있는 유연성을 제공한다.
본 논문에서는 이러한 RoboVLMs의 강점을 활용하여, 제한된 하드웨어 자원 내에서 모바일 로봇이 자연어 명령을 수행할 수 있는 통합 시스템 가이드를 제시한다. 결과적으로 본 연구는 자원이 제한된 모바일 로봇 하드웨어에서도 고성능 VLA 모델이 탑재될 수 있으며, 이것이 기존의 단순화된 경량 모델보다 훨씬 높은 수준의 자율 주행 지능을 제공할 수 있음을 보여준다.

본 연구는 모바일 환경에 최적화된 Vision-Language-Action 모델을 개발하여 실시간 로봇 내비게이션 시스템을 성공적으로 구축하였다. 최신 V3-exp08 및 V4 연계 실험 결과, Jetson Orin NX에서 최고 97.9%~100.0%의 검증 정확도를 기록하며 실환경 미션 성공률 90%를 달성하였다. 이를 통해 자원 제약적인 하드웨어에서도 대형 VLM의 지능을 활용한 정밀 제어 시스템 구현이 가능함을 입증하였다.


REFERENCES 
   [1] Y. Ma, S. Gervet, Y. Zeng, A. Suhr, A. Aljundi, J. Malik, D. Batra, A. Rai, S. Levine, "Towards Generalist Robot Policies: What Matters in Building Vision-Language-Action Models," arXiv preprint arXiv:2401.08526, 2024.
[2] H. Yang and I. Choi, "Mobile-Optimized Vision-Language-Action Model for Real-Time Robot Navigation: A Hybrid Architecture Approach," Journal of Computer and Information, 2024.
[3] A. Brohan, N. Brown, J. Carbajal, Y. Chebotar, J. Dabis, C. Finn, K. Gopalakrishnan, K. Hausman, A. Herzog, J. Hsu, J. Ibarz, B. Ichter, A. Irpan, T. Jang, R. Julian, D. Kalashnikov, Y. Kuang, I. Leichty, S. Levine, Y. Lu, U. Malla, D. Manjunath, I. Mordatch, R. Nachum, C. Parada, J. Peralta, E. Perez, K. Pertsch, J. Quiambao, K. Rao, M. Ryoo, G. Salazar, P. Sanketi, P. Sermanet, J. Sievers, C. Tan, A. Toshev, V. Vanhoucke, F. Xia, T. Xiao, P. Xu, S. Xu, M. Yan, A. Zeng, "RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control," Conference on Robot Learning, 2023.
[4] A. Brohan, Y. Chebotar, C. Finn, K. Hausman, K. Gopalakrishnan, A. Irpan, P. Sermanet, S. Levine, "RT-1: Robotics Transformer for Real-World Control at Scale," Conference on Robot Learning, 2023.
[5] D. Shah, B. Osiński, S. Levine, "LM-Nav: Robotic Navigation with Large Pre-Trained Models of Language, Vision, and Action," Conference on Robot Learning, 2022.
[6] Y. Ma, D. Jayaraman, O. Bastani, "VL-Nav: Vision-and-Language Navigation in the Real World," Conference on Computer Vision and Pattern Recognition, 2023.
[7] Y. Jiang, A. Gupta, Z. Zhang, G. Wang, Y. Dou, Y. Chen, L. Fei-Fei, A. Anandkumar, Y. Zhu, L. Fan, "MoManipVLA: Mobile Manipulation with Vision-Language-Action Models," arXiv preprint arXiv:2310.10221, 2023.
[8] S. Huang, W. Xiong, W. Y. Wang, "CogVLA: Vision-Language-Action Model for Cognitive Robots," arXiv preprint arXiv:2311.00899, 2023.
[9] A. Majumdar, A. Shrivastava, S. Lee, P. Anderson, D. Batra, D. Parikh, "Narrate2Nav: Navigate Like a Human," Conference on Computer Vision and Pattern Recognition, 2020.
[10] A. Radford, J. W. Kim, C. Hallacy, A. Ramesh, G. Goh, S. Agarwal, G. Sastry, A. Askell, P. Mishkin, J. Clark, G. Krueger and I. Sutskever, "Learning Transferable Visual Models From Natural Language Supervision," International Conference on Machine Learning, 2021.
[11] S. Huang, W. Xiong, W. Y. Wang, "Machine Comprehension with Syntax-Aware Framework," Proceedings of the 55th Annual Meeting of the Association for Computational Linguistics, 2017.
[12] H. Touvron, M. Cord, M. Douze, F. Massa, A. Sablayrolles, H. Jegou, "Training data-efficient image transformers & distillation through attention," International Conference on Machine Learning, 2021.
[13] A. Dosovitskiy, L. Beyer, A. Kolesnikov, D. Weissenborn, X. Zhai, T. Unterthiner, M. Dehghani, M. Minderer, G. Heigold, S. Gelly, J. Uszkoreit, N. Houlsby, "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale," International Conference on Learning Representations, 2021.
[14] K. He, X. Zhang, S. Ren and J. Sun, "Deep Residual Learning for Image Recognition," The Computer Vision and Pattern Recognition, Dec 2015. https://doi.org/10.48550/arXiv.1512.03385
[15] A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, L. Kaiser and I. Polosukhin, "Attention Is All You Need," 31st Conference on Neural Information Processing Systems, Long Beach, CA, USA, Jun 2017. https://doi.org/10.48550/arXiv.1706.03762
[16] J. Devlin, M. W. Chang, K. Lee, K. Toutanova, "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding," North American Chapter of the Association for Computational Linguistics, 2019.
[17] S. Hochreiter, J. Schmidhuber, "Long Short-Term Memory," Neural Computation, Vol. 9, No. 8, pp. 1735-1780, 1997.



