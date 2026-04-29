# 2026-04-24 교수님 미팅 발표 스크립트

## 2분 버전

안녕하세요. 현재 상태를 먼저 한 줄로 말씀드리면, 지금 practical baseline은 `exp25`이고, 전체 모델이 안 되는 상황이라기보다 `turning commitment` failure slice가 남아 있는 상황입니다.

`exp25`는 closed-loop success가 `55.6%`, mean FPE가 `0.382`입니다. 특히 `center_left`, `center_right`, `center_straight`, `left_straight`, `right_straight`는 전부 closed-loop `100%`입니다. 즉 목표를 보면서 직진하고 중앙 정렬하는 계열은 이미 됩니다.

문제는 turning family입니다. `left_left`, `left_right`, `right_left`, `right_right`는 전부 closed-loop `0%`입니다. 그래서 지금 핵심 병목은 accuracy가 아니라, 초반 몇 프레임에서 어느 방향으로 돌기 시작할지에 대한 정책 일관성이 무너지는 점입니다.

이 점은 `exp26`이 잘 보여줍니다. `exp26`은 PM/DM가 `70.24%`로 offline 수치만 보면 가장 좋아 보이지만, 실제 closed-loop는 `0.0%`입니다. 그래서 이번에는 offline 숫자보다 rollout 기준으로 모델을 선택해야 합니다.

또 하나는 교수님께서 질문하실 수 있는 human-reviewed bbox GT 부분입니다. 이 부분은 저희도 바로 효과가 날지 보기 위해 `exp29`, `exp30` short ablation을 돌렸습니다. 그런데 5-epoch 결과에서 둘 다 bbox IoU가 `0.0`이었고, `FORWARD`, `LEFT`, `RIGHT`도 회복되지 않았습니다. 즉 GT가 틀렸다는 뜻은 아니고, 현재 head/loss 구조로는 GT를 줘도 usable bbox와 left/right policy 회복으로 연결되지 않는다는 뜻입니다.

그래서 현재 메시지는 명확합니다. `exp25`를 practical baseline으로 유지하고, 그 위에서 turning family와 grounding supervision이 실제로 경쟁력 있게 작동하도록 `exp28` 계열을 보강하고 있습니다. 오늘은 이 방향으로 active fix in progress로 보고드리는 것이 가장 정확합니다.

## 5분 버전

오늘은 크게 세 가지로 말씀드리겠습니다. 첫째, 현재 기준 모델이 무엇인지. 둘째, 왜 아직 실전성이 부족한지. 셋째, 그래서 지금 어떤 방향으로 수정하고 있는지입니다.

첫 번째로 현재 기준 모델입니다. 최근 후보들 중 practical baseline은 `exp25`입니다. 수치로는 closed-loop success `55.6%`, mean FPE `0.382`, mean TLD `0.936`, PM/DM `52.38%`입니다. 중요한 점은 이 모델이 이미 되는 시나리오가 분명하다는 것입니다. `center_left`, `center_right`, `center_straight`, `left_straight`, `right_straight`는 closed-loop가 모두 `100%`입니다. 즉 목표를 보면서 직진하고 정렬하는 계열은 이미 안정적으로 통과합니다.

두 번째로 남아 있는 병목입니다. 지금 문제를 전체 모델 실패로 보면 안 됩니다. 실패는 특정 family에 집중되어 있습니다. `left_left`, `left_right`, `right_left`, `right_right`는 모두 closed-loop `0%`입니다. 해석하면, 모델이 목표를 찾거나 직진하는 것은 되는데, 초반 몇 프레임 안에 turn을 시작해야 하는 시점에서 결심이 무너집니다. 그래서 지금 핵심 병목은 accuracy가 아니라 `turning commitment collapse`입니다.

이 점은 `exp26`이 가장 잘 보여주는 반례입니다. `exp26`은 PM/DM `70.24%`로 offline 기준으로는 가장 좋아 보이지만, 실제 closed-loop는 `0.0%`였습니다. 반대로 `exp25`는 offline은 더 낮아도 rollout은 가장 낫습니다. 따라서 이번 미팅에서는 모델 선택 기준을 offline이 아니라 rollout으로 두는 것이 맞다고 말씀드리는 게 중요합니다. `exp27`의 letterbox 가설도 같은 맥락입니다. closed-loop가 `33.3%` 수준이라 현재는 개선안이라기보다 ablation reference로 보는 편이 정확합니다.

세 번째는 human-reviewed bbox GT에 대한 부분입니다. 자연스럽게 드는 질문은, 사람이 검수한 bbox GT를 넣으면 바로 해결되는 것 아닌가 하는 점입니다. 저희도 이 가설을 빠르게 확인하기 위해 `exp29`, `exp30` short ablation을 돌렸습니다. `exp29`는 coarse-only, `exp30`은 bbox+coarse 설정이었고 둘 다 5 epochs였습니다. 결과는 둘 다 bbox IoU가 `0.0`, `FORWARD`, `LEFT`, `RIGHT` recovery도 실패였습니다. PM/DM도 `exp29`가 `21.43%`, `exp30`이 `14.29%` 수준이었습니다.

이 결과는 두 가지를 의미합니다. 첫째, GT가 틀린 것은 아닙니다. 둘째, 그렇다고 GT를 넣는 것만으로 바로 해결되는 것도 아닙니다. 현재 구조에서는 auxiliary bbox/coarse loss가 action loss와의 경쟁에서 너무 약하게 작동하고 있습니다. 실제 정리해 보면 `exp28~30`도 validation loss 기준으로는 base action loss가 약 `99.6%`를 차지합니다. 그래서 bbox head는 tiny center box로 collapse하고, coarse는 center bias만 강화되며, 결국 left/right policy recovery로 이어지지 않았습니다.

그래서 현재 방향은 `exp25`를 버리는 것이 아니라, `exp25`를 rollout baseline으로 유지하면서 turning family와 grounding supervision이 shared feature를 실제로 바꾸도록 구조를 보강하는 쪽입니다. `exp28`이 그 첫 단계였고, 오늘인 2026-04-24에는 `exp31`에서 고정 lambda 대신 learned loss mixing을 적용한 follow-up 5-epoch run도 완료된 상태입니다. 다만 이건 아직 rollout 평가가 남아 있으므로, 오늘 보고에서는 결과가 아니라 진행 중인 corrective action으로 설명하는 것이 맞습니다.

정리하면, 현재 가장 정확한 메시지는 이렇습니다. 첫째, `exp25`가 practical baseline입니다. 둘째, 남은 문제는 전체 실패가 아니라 turning family failure slice입니다. 셋째, `exp26`이 보여주듯 offline metric은 rollout을 보장하지 않습니다. 넷째, human-reviewed bbox GT도 현재 구조에서는 바로 해결책이 아니었습니다. 따라서 오늘은 `exp25 baseline + exp28~31 active fix in progress`로 보고드리는 것이 가장 정직하고 기술적으로도 맞습니다.
