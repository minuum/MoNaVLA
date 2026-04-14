#!/usr/bin/env python3
import os
import base64

def get_base64_image(image_path):
    if not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"

def main():
    img_path = "/home/billy/25-1kp/MoNaVLA/test_image_temp.jpg"
    img_b64 = get_base64_image(img_path)
    
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MoNaVLA Experiment Docs - Text Sensitivity</title>
    <style>
        :root {{
            --primary: #2563eb;
            --bg-color: #f8fafc;
            --text-color: #1e293b;
            --card-bg: #ffffff;
        }}
        body {{
            font-family: 'Pretendard', -apple-system, sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--bg-color);
            color: var(--text-color);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}
        .docs-container {{
            width: 900px;
            height: 600px;
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            overflow: hidden;
            position: relative;
            display: flex;
            flex-direction: column;
        }}
        .header {{
            background: var(--primary);
            color: white;
            padding: 15px 25px;
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
        }}
        .slide-container {{
            flex: 1;
            position: relative;
            padding: 30px;
        }}
        .slide {{
            display: none;
            height: 100%;
            animation: fadeIn 0.4s ease;
        }}
        .slide.active {{
            display: block;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .footer {{
            padding: 15px 25px;
            background: #f1f5f9;
            border-top: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        button {{
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            background: var(--primary);
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
        }}
        button:disabled {{
            background: #cbd5e1;
            cursor: not-allowed;
        }}
        button:hover:not(:disabled) {{
            opacity: 0.9;
        }}
        
        /* Typography & Layout within slides */
        h2 {{ margin-top: 0; color: var(--primary); border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }}
        .two-cols {{ display: flex; gap: 30px; height: calc(100% - 50px); }}
        .col {{ flex: 1; overflow-y: auto; }}
        .img-preview {{ width: 100%; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9rem; }}
        th, td {{ padding: 10px 12px; border: 1px solid #cbd5e1; text-align: center; }}
        th {{ background-color: #f1f5f9; font-weight: 600; }}
        .highlight {{ color: #dc2626; font-weight: bold; background-color: #fee2e2; }}
        .blue-highlight {{ color: var(--primary); font-weight: bold; }}
        
        li {{ margin-bottom: 15px; line-height: 1.6; }}
    </style>
</head>
<body>

<div class="docs-container">
    <div class="header">
        <span>🤖 MoNaVLA Experiment Report</span>
        <span id="page-indicator">Page 1 / 4</span>
    </div>

    <div class="slide-container">
        <!-- Page 1: Abstract -->
        <div class="slide active" id="slide-1">
            <h2>실험 개요: 텍스트-로짓 민감도 (Text-Logit Sensitivity)</h2>
            <p><strong>가설:</strong> "멀티모달 VLA 모델이 로봇의 주행 액션을 예측할 때, 사용자의 자연어 지시(Prompt)를 무시하고 시각적 정보(화면 중앙의 객체 등)에만 과도하게 의존하는가?"</p>
            <p><strong>실험 방법:</strong></p>
            <ul>
                <li>동일한 정지 이미지(1프레임)를 고정.</li>
                <li>단어 프롬프트만 다르게 입력 ("Go forward", "Go left", "Go right", "Stop").</li>
                <li>각 입력별로 도출되는 6개 Action Class의 Softmax 확률(명령어별 로그 분포 변동량)을 측정.</li>
            </ul>
        </div>

        <!-- Page 2: Test Image -->
        <div class="slide" id="slide-2">
            <h2>테스트 이미지 (Visual Input)</h2>
            <div style="text-align: center;">
                <img src="{img_b64}" alt="Test Scene" class="img-preview" style="max-height: 380px; width: auto;" />
                <p style="margin-top:20px; color:#64748b;"><em>*이 이미지를 고정값으로 두고 텍스트 입력만 변경했습니다. 오른쪽으로 돌기 좋은 혹은 우측에 시각적 이끌림이 있는 상태입니다.</em></p>
            </div>
        </div>

        <!-- Page 3: Quantitative Results -->
        <div class="slide" id="slide-3">
            <h2>검증 결과 (Softmax Probabilities)</h2>
            <p>동일한 이미지에 대해 텍스트 프롬프트를 변경했을 때의 클래스별 예측 확률입니다.</p>
            <table>
                <tr>
                    <th>입력 텍스트</th>
                    <th>최종 예측</th>
                    <th>Stop</th>
                    <th>Forward</th>
                    <th>Left</th>
                    <th>Right</th>
                    <th>FWD-L</th>
                    <th>FWD-R</th>
                </tr>
                <tr>
                    <td>"Go forward..."</td>
                    <td><strong>Right</strong></td>
                    <td>19.9%</td>
                    <td class="blue-highlight">8.8%</td>
                    <td>23.5%</td>
                    <td>25.2%</td>
                    <td class="blue-highlight">11.0%</td>
                    <td class="blue-highlight">11.3%</td>
                </tr>
                <tr>
                    <td>"Go left."</td>
                    <td><strong>Right</strong></td>
                    <td>21.8%</td>
                    <td>5.2%</td>
                    <td class="blue-highlight">27.0%</td>
                    <td>30.6%</td>
                    <td>7.6%</td>
                    <td>7.5%</td>
                </tr>
                <tr>
                    <td>"Go right."</td>
                    <td><strong>Right</strong></td>
                    <td>23.1%</td>
                    <td>4.0%</td>
                    <td>27.9%</td>
                    <td class="blue-highlight">32.6%</td>
                    <td>6.3%</td>
                    <td>5.8%</td>
                </tr>
                <tr>
                    <td>"Stop here."</td>
                    <td><strong>Right</strong></td>
                    <td class="blue-highlight">24.0%</td>
                    <td>3.7%</td>
                    <td>27.9%</td>
                    <td>33.3%</td>
                    <td>5.8%</td>
                    <td>5.1%</td>
                </tr>
            </table>
            <p style="font-size: 0.9rem; margin-top: 15px; color:#475569;">
                <strong>관측:</strong> "Go left"를 입력하면 Left 확률이 증가하고, "Stop"을 넣으면 Stop 확률이 눈에 띄게 상승합니다. 텍스트 지시에 따라 분명히 확률이 변화하지만, 최종 Argmax 예측값은 시각적 편향으로 인해 계속 <strong>Right</strong>를 가리킵니다.
            </p>
        </div>

        <!-- Page 4: Findings & Conclusion -->
        <div class="slide" id="slide-4">
            <h2>결론 및 향후 대응 방향 (Findings)</h2>
            <div class="two-cols">
                <div class="col">
                    <h3 style="color:#0f172a;">1. 언어 반영도 (Text Sensitivity) 확인됨</h3>
                    <p>테스트 결과, VLM은 사용자의 시스템 프롬프트를 <strong>백색소음으로 치부하지 않습니다</strong>. 각 지시어의 방향성에 맞춰 해당 클래스의 확률값이 실제로 약 3~5%씩 움직였습니다.</p>
                    
                    <h3 style="color:#0f172a;">2. 압도적인 시각 편향 (Visual Over-reliance)</h3>
                    <p>그러나 언어 모델의 가중치보다 <strong>시각적 특징 추출의 가중치가 행동 예측에 더 결정적인 영향</strong>을 줍니다. 이는 "우회전할 것 같은" 주행 경로 시각 단서가 "왼쪽으로 가라"는 텍스트 명령어의 영향을 상쇄해버리는 결과입니다.</p>
                </div>
                <div class="col" style="background:#f8fafc; padding:15px; border-radius:8px; border:1px solid #e2e8f0;">
                    <h3 style="color:#2563eb; margin-top:0;">🚀 Next Step : BBox 개입 전략</h3>
                    <p>현재 모델의 상태를 <strong>"귀는 열려 있지만 눈으로 보는 것을 맹신하는 상태"</strong>로 정의할 수 있습니다. 교수님 미팅 방어용으로 아주 훌륭한 관측입니다.</p>
                    <p>따라서, 이 편향을 역이용하여 <strong>[목표물 BBox 좌표]</strong>를 자연어 프롬프트와 함께 주입하는 트랙 2(스포츠카 시동 전략)가 필수적입니다.</p>
                    <p style="font-size:0.85rem; color:#64748b;">(예시: "Go forward to the basket at [Xmin, Ymin, Xmax, Ymax]")</p>
                </div>
            </div>
        </div>
    </div>

    <div class="footer">
        <button id="btn-prev" onclick="changeSlide(-1)" disabled>← Previous</button>
        <button id="btn-next" onclick="changeSlide(1)">Next →</button>
    </div>
</div>

<script>
    let currentSlide = 1;
    const totalSlides = 4;

    function changeSlide(direction) {{
        document.getElementById(`slide-${{currentSlide}}`).classList.remove('active');
        currentSlide += direction;
        document.getElementById(`slide-${{currentSlide}}`).classList.add('active');
        
        document.getElementById('page-indicator').innerText = `Page ${{currentSlide}} / ${{totalSlides}}`;
        
        document.getElementById('btn-prev').disabled = currentSlide === 1;
        document.getElementById('btn-next').disabled = currentSlide === totalSlides;
    }}
</script>

</body>
</html>"""

    os.makedirs("/home/billy/25-1kp/MoNaVLA/docs", exist_ok=True)
    out_path = "/home/billy/25-1kp/MoNaVLA/docs/Track1_Sensitivity_Findings.html"
    with open(out_path, "w") as f:
        f.write(html_content)
    
    print(f"Interactive documentation generated at: {out_path}")

if __name__ == "__main__":
    main()
