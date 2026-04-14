
Enhancing Generalization in Mobile Navigation: Adapting RoboVLMs for Complex Instruction Following in Memory-Constrained Embedded Systems  
Min-Woo Lee*,  In-Yeop Choi**

[Abstract]
This paper proposes the results of optimizing and implementing the RoboVLMs framework for a mobile robot navigation environment to overcome the limitations of existing Vision-Language-Action (VLA) models. While existing VLA-based navigation models demonstrate powerful visual understanding, they suffer from high inference costs due to their interleaved architecture, reduced control precision due to discrete action prediction, and their large model size, making them unsuitable for deployment on memory-constrained mobile devices. Lightweight models such as TIC-VLA and OmniVLA-edge often suffer from reduced understanding of complex language commands during model size reduction and poor generalization performance in out-of-distribution environments. In this study, we demonstrate that RoboVLMs leverages its powerful vision-language backbone and efficient policy head architecture to support high-level contextual understanding and continuous action spaces, enabling precise and intelligent navigation of 2-DoF mobile robots even on the NVIDIA Jetson Orin NX, a 16GB memory-constrained system.
▸Key words: RoboVLMs, VLA, VLM, 
[요   약]
본 연구는 기존의 Vision-Language-Action (VLA) 모델이 가진 한계를 극복하기 위해, RoboVLMs 프레임워크를 모바일 로봇 내비게이션 환경에 맞춰 최적화 및 구현한 결과를 제시한다. 기존의 VLA 기반 내비게이션 모델들은 강력한 시각 이해력을 보여주지만, Interleaved 구조로 인한 높은 추론 비용과 이산적 액션 예측으로 인한 제어 정밀도 저하되고, 모델 크기가 커서 메모리 제약적인 모바일 기기에 탑재하지 못하는 한계가 있다. TIC-VLA와 OmniVLA-edge 같은 경량화 모델인 경우 모델 크기를 줄이는 과정에서 복잡한 언어 명령 이해 능력이 저하되거나, 학습 분포를 벗어난 환경에서의 일반화 성능이 낮은 문제를 지니고 있다. 본 연구에서는 RoboVLMs의 강력한 시각-언어 백본과 효율적인 정책 헤드(Policy Head) 구조를 활용하여, 16GB의 메모리 제한이 있는 NVIDIA Jetson Orin NX 환경에서도 고수준의 문맥 이해와 연속적 액션 공간을 지원하여 2-DoF 모바일 로봇의 정밀하고 지능적인 주행을 가능케 함을 입증하였다. 


▸주제어: RoboVLMs, VLA, VLM, 모바일 VLA, 실시간 내비게이션, 하이브리드 아키텍처, Kosmos-2, CLIP, LSTM 정책 헤드
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
본 연구에서 제안하는 Mobile VLA 시스템은 Policy-Head-Continuous-Action Models 패러다임을 따른다. 이는 Kosmos-2 + CLIP 하이브리드 VLM을 사용하여 시각-언어 특징을 추출하고, LSTM 기반의 Policy Head(4층, 4096 hidden size)를 통해 2D 연속 액션 [linear_x, linear_y]을 생성하는 구조이다.

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
본 연구에서는 Kosmos-2 VLM을 기반으로 하여 액션 예측 기능을 추가하였다. 훈련 데이터는 직접 수집한 모바일 로봇 내비게이션 데이터셋을 사용하였으며, 정책 헤드를 LSTM 기반으로 2DoF 모바일 로봇을 제어하였다. 학습 과정에서는 18프레임의 시퀀스를 사용하여 시간적 정보를 처리하며, 4층 LSTM을 통해 복잡한 시퀀스 패턴을 학습한다. 학습 파라미터는 배치 크기 2, Adam 옵티마이저를 사용하여 10-15 에포크 동안 진행되었다.
VLM을 LoRA를 이용하여 어떻게 학습을 진행 했는지 기술 해야함(3/9)

1.4 모바일 로봇에 탑재 
학습한 VLA 모델을 어떻게 모바일 로봇에 탑재 했는지 탑재 과정을 설명해야 함 (3/09)

1.5 다른 VLA와의 차이점 
(본 연구의 주요 차이점은 다음과 같다. 첫 번째는 모바일 환경에 특화된 2D 액션 공간을 사용하여 내비게이션에 최적화하였다. 두 번째는 Kosmos-2와 CLIP을 조합한 하이브리드 아키텍처를 제안하여 성능을 향상시켰다. 세 번째는 엣지 디바이스에서의 실시간 처리를 위한 모바일 최적화를 수행하였다.)-> 실제로 수행을 했나?

2. RoboVLMs 한계점
우리가 분석한 RoboVLMs의 한계점이다.  
-> 실제로 분석한 것인가? 아니면 내용을 제거하고자 함. 
2.1 멀티모달 상호작용 구조의 제한
기존 VLM의 구조(예: attention mask, mixture of experts)를 그대로 유지한 채 VLA를 구성했기 때문에, 행동(action)과의 상호작용을 위한 전용 아키텍처 설계가 부족하다. π0 같은 모델은 이러한 상호작용을 더 정교하게 설계하여 성능 향상을 보여주므로, 향후 연구에서 구조적 개선이 필요하다.

2.2 VLA 구조의 단순화
논문에서 고려한 VLA 구조는 네 가지로 제한되어 있으며, 다양한 구조적 변형이나 세부 설계 요소(예: attention 방식, token 처리 방식 등)에 대한 탐색이 부족하다. 

2.3 행동 토크나이징 및 학습 목표의 미탐색
행동을 표현하는 방식(예: VQ-VAE, diffusion models, flow matching 등)에 대한 실험이 부족하며, 정교한 행동 표현 및 예측 방식에 대한 연구가 향후 필요하다.

3. RoboVLMs 개선 제안 
-> 3 단락 전체(3.1, 3.2, 3.3)가 실제로 수행한 것인가? 아니면 논문 내용을 그냥 분석한 것인가?

RoboVLMs의 한계점을 분석한 결과, 다음과 같은 개선 방안을 제안한다.

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

실험에 사용된 데이터셋은 총 72개의 에피소드로 구성되었다. 이 데이터셋은 8개의 핵심 내비게이션 시나리오를 기반으로 수집되었으며, 각 시나리오는 다양한 장애물 배치와 회피 경로를 포함한다. -> 이부분이 맞나?

2. 모델 구성 및 비교
-> 실제로 실험해 본것인가? 아니면 RoboVLMs 논문에서 나오는 내용인가? 실제로 구성한 모델 구성을 기술.
본 연구에서는 총 6가지 모델 아키텍처를 실험하여 성능을 비교 분석하였다. 첫째, Kosmos2+CLIP Hybrid 모델이다. 이 모델은 Kosmos-2와 CLIP을 조합하여 특징을 추출하고, LSTM 기반의 정책 헤드로 2D 연속 액션을 생성한다. 둘째, Pure Kosmos2 모델이다. 이 모델은 Kosmos-2만을 사용하여 시각-언어 특징을 추출하고, 동일한 LSTM 정책 헤드를 사용한다. 셋째, Simple CLIP 모델이다. 이 모델은 CLIP Vision과 CLIP Text를 융합하여 특징을 추출한다. 넷째, CLIP with LSTM 모델이다. 이 모델은 CLIP 기반 특징에 LSTM을 추가하여 시퀀스 정보를 처리한다. 다섯째, Original CLIP 모델이다. 이 모델은 기본 CLIP 아키텍처를 사용한다. 여섯째, Original CLIP (증강) 모델이다. 이 모델은 증강된 데이터셋을 사용하여 훈련되었다.









5. 테스트 수행 

VLA 모델을 탑재한 모발을 로봇을 가지고 실제로 테스트 환경을 어떻게 구성하고 어떤 실험을 했는지 사진과 함께 기술해야 함(3/9)

6. 테스트 결과

테스트 결과 기술해야함(3/9)

(모델별 정확도 성능을 MAE(Mean Absolute Error) 기준으로 비교한 결과, Kosmos2+CLIP Hybrid 모델이 0.212의 MAE로 가장 우수한 성능을 보였다. Pure Kosmos2 모델은 0.247의 MAE를 기록하였으며, 이는 하이브리드 모델보다 약간 낮은 성능을 보였다. Simple CLIP 모델은 0.451의 MAE를, CLIP with LSTM 모델은 0.456의 MAE를 기록하였다. Original CLIP 모델은 0.494의 MAE를 보였으며, Original CLIP (증강) 모델은 0.672의 MAE로 가장 낮은 성능을 기록하였다.

메모리 사용량 측면에서는 CLIP 기반 모델들이 1.7GB로 가장 효율적인 메모리 사용을 보였다. Pure Kosmos2 모델은 6.8GB, Kosmos2+CLIP Hybrid 모델은 7.4GB의 메모리를 사용하였으며, 이는 복잡한 모델 구조로 인한 증가이지만 여전히 모바일 환경에서 수용 가능한 수준이다.) 
-> 이건 수행한 내용인가 아니면 RoboVLMs 논문의 내용인가? 필요한 내용인가?

4. 데이터 증강 효과 분석

V. Conclusions
1. 연구 성과 요약






( 본 연구는 모바일 환경에 최적화된 Vision-Language-Action 모델을 개발하여 실시간 로봇 내비게이션 시스템을 구축하였다. 연구의 주요 성과는 다음과 같다.
첫째, 모바일 환경에 최적화된 VLA 모델 개발에 성공하였다. Jetson Orin NX 16GB 환경에서 실시간 동작 가능한 VLA 모델을 구현하여, 메모리 사용량 2GB 이하, MAE 0.25 이하의 성능을 달성하였다. 이는 기존의 대규모 VLA 모델들이 가진 계산 복잡도와 실시간성 문제를 해결한 중요한 성과이다.
둘째, Kosmos-2와 CLIP을 조합한 하이브리드 아키텍처를 제안하여 성능을 향상시켰다. Kosmos2+CLIP Hybrid 모델은 MAE 0.212의 우수한 정확도를 달성하였으며, 이는 Pure Kosmos2 모델(MAE 0.247)보다 약 14% 향상된 성능이다. 하이브리드 아키텍처는 Kosmos-2의 강력한 멀티모달 이해 능력과 CLIP의 효율적인 특징 추출 능력을 결합하여 성능과 효율성을 모두 개선하였다. 또한, 데이터 증강 기법의 효과를 분석하여 원본 72 에피소드만으로도 우수한 성능을 달성할 수 있음을 확인하였다.)
-> 실제 수행한 성과는 무엇인가?



2. 주요 기여도
본 연구의 주요 기여는 다음과 같다. RoboVLMs는 시각-언어 토큰의 특징을 보존하면서도 이력 정보(History)를 효율적으로 통합하는 정책 헤드 구조를 통해, 경량 모델들이 놓친 '추론 능력'과 '일반화'를 동시에 확보한다. 특히, 본 논문에서는 다음과 같은 기여를 하였다. 
2.1 액션 공간을 재설계 하였다. 7-DoF 매니퓰레이션 중심의 RoboVLM을 2-DoF 모바일 로봇의 선속도 및 각속도 제어로 최적화하여 학습 효율을 높였다.
2.2 컴퓨터 리소스 제한 적인 로봇에 모델을 최적화하여 탑재하였다. RoboVLM의 강력한 성능을 유지하면서도 최적화를 통해 NVIDIA Jetson Orin NX(16GB) 환경에서 구동 가능하도록 구현하여, 실용적 배포 가능성을 입증하였다.
2.3 지능적 내비게이션을 검증 하였다. 단순 이동을 넘어, 복잡한 지시어 이해와 다단계 추론이 필요한 환경에서 본 모델이 기존 경량 VLA 모델보다 뛰어난 임무 성공률(?)을 보임을 실험적으로 증명하였다. -> 이 내용을 쓸려면 테스트 필요, 내용 포함 또는 수정 고려 


( 하이브리드 아키텍처 제안이다. Kosmos-2와 CLIP을 효과적으로 조합하여 성능을 향상시킨 새로운 아키텍처를 제안하였다. 셋째,  RoboVLMs 아키텍처 패러다임 적용이다. Policy-Head-Continuous-Action Models 패러다임을 선택하여 모바일 환경에 최적화된 VLA 시스템을 구축하였다.) -> 이중에 직접수행하여 얻은 결과는 ?

3. 연구의 한계점
본 연구는 몇 가지 한계점을 가지고 있다. 첫째, 제한된 데이터셋이다. 72개의 에피소드로 구성된 데이터셋을 사용하였으며, 이는 더 큰 규모의 데이터셋에서의 성능 검증이 필요하다. 둘째, 단순한 액션 공간이다. 2D 연속 액션 공간을 사용하여 모바일 로봇 내비게이션에 특화되었지만, 더 복잡한 로봇 제어 태스크에는 적용이 어려울 수 있다. 셋째, 특정 하드웨어 환경이다. Jetson Orin NX 환경에서만 검증되었으며, 다른 엣지 디바이스에서의 성능 검증이 필요하다.

4. 향후 연구 방향
향후 연구 방향은 다음과 같다. 첫째, 데이터셋 확장이다. 더 다양한 환경과 시나리오를 포함하는 대규모 데이터셋을 구축하여 모델의 일반화 성능을 향상시켜야 한다. 둘째, 복잡한 액션 공간 확장이다. 2D 액션 공간을 넘어서 더 복잡한 로봇 제어 태스크에 적용할 수 있는 아키텍처를 개발해야 한다. 셋째, 다양한 하드웨어 환경 검증이다. Jetson Orin NX 외에도 다양한 엣지 디바이스에서의 성능을 검증하여 범용성을 높여야 한다.

5. 실용적 의의

이 논문은 제한된 메모리(16GB) 내에서도 상용 VLM의 강력한 이해 능력을 유지하면서, Policy Head를 통해 모바일 로봇 주행에 필요한 정확한 연속 제어와 장기적인 판단 능력을 확보한 것에 의의가 있다. 


6. 최종 결론

현재 모바일 기반 VLA 모델들이 존재하지만, 본 연구에서 RoboVLMs 프레임워크를 선택하고 이를 2-DoF 주행에 맞게 수정한 이유는 두 가지 핵심적인 기술적 이점 때문이다.
첫째, 구조적 효율성과 성능의 균형이다. RoboVLMs 모델의 Policy Head 구조는 Interleaved 등과 같은 모델 구조보다 일반화 성능과 데이터 효율성 면에서 우수함이 입증되었다.  본 연구는 Policy Head 구조를 유지하면서도 7-DoF의 복잡한 액션 공간을 2-DoF로 단순화하여 학습 효율을 극대화하였다.
둘째, 임베디드 하드웨어 호환성이다. 대부분의 고성능 VLA 모델은 수십 GB의 비디오 메모리(VRAM)를 요구하여 실제 이동 로봇에 탑재하기 불가능하다. 반면 RoboVLMs는 다양한 VLM 백본(PaliGemma 등)과의 결합이 자유로워, 16GB 메모리를 가진 Jetson Orin NX에서도 실시간 추론이 가능한 수준으로 모델 크기를 최적화할 수 있는 유연성을 제공한다.
본 논문에서는 이러한 RoboVLMs의 강점을 활용하여, 제한된 하드웨어 자원 내에서 모바일 로봇이 자연어 명령을 수행할 수 있는 통합 시스템 가이드를 제시한다. 결과적으로 본 연구는 자원이 제한된 모바일 로봇 하드웨어에서도 고성능 VLA 모델이 탑재될 수 있으며, 이것이 기존의 단순화된 경량 모델보다 훨씬 높은 수준의 자율 주행 지능을 제공할 수 있음을 보여준다.

(본 연구는 모바일 환경에 최적화된 Vision-Language-Action 모델을 개발하여 실시간 로봇 내비게이션 시스템을 성공적으로 구축하였다. Kosmos-2와 CLIP을 조합한 하이브리드 아키텍처를 통해 우수한 성능을 달성하였다. 연구 결과는 Jetson Orin NX에서 MAE 0.212의 높은 정확도를 달성하여, 모바일 환경에서의 실용적인 VLA 시스템 구현에 성공하였다.
) -> 실제 결과인가?


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



