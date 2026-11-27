"""Writes web/i18n/{ko,ja,en}.json. Source of the participant texts: project doc 2026-11-24_pilot2_site_text.
Each entry is (ko, ja, en). Run: python tools/make_i18n.py"""
import json, os
T = {
 "title": ("청취 실험", "聴取実験", "Listening experiment"),
 "next": ("다음", "次へ", "Next"), "start": ("시작", "開始", "Start"), "play": ("재생", "再生", "Play"), "stop": ("정지", "停止", "Stop"), "replay": ("다시 듣기", "もう一度聞く", "Listen again"),
 "loading": ("소리를 불러오는 중입니다…", "音を読み込んでいます…", "Loading sounds…"),
 "loadError": ("소리를 불러오지 못했습니다. 인터넷 연결을 확인한 뒤 다시 시도해 주십시오.", "音を読み込めませんでした。インターネット接続を確認して、もう一度お試しください。", "The sounds could not be loaded. Please check your connection and try again."),
 "retry": ("다시 시도", "再試行", "Try again"),
 "resumeQ": ("진행 중이던 실험이 있습니다. 이어서 하시겠습니까?", "途中まで進めた実験があります。続きから再開しますか。", "An unfinished session was found. Continue where you left off?"),
 "resumeYes": ("이어서 하기", "続きから", "Continue"), "resumeNo": ("처음부터", "最初から", "Start over"),
 "seatL": ("왼쪽", "左", "left"), "seatC": ("가운데", "中央", "centre"), "seatR": ("오른쪽", "右", "right"),
 "stage": ("무대", "舞台", "Stage"), "singer": ("가수", "歌手", "Singer"), "you": ("내 자리", "自分の席", "Your seat"), "speaker": ("스피커", "スピーカー", "Loudspeaker"),

 "introH": ("실험 안내", "実験について", "About this experiment"),
 "intro": ("<p>이 실험에서는 콘서트홀 객석에 앉아 공연을 듣는 상황을 헤드폰으로 재현합니다. 무대 위에서 소프라노가 오케스트라와 함께 노래하고, 소프라노의 목소리는 무대 양옆 스피커(PA)로 보강됩니다.</p><p>여러분은 객석의 세 자리(왼쪽·가운데·오른쪽)에 차례로 앉아, 소프라노의 노래가 어떻게 들리는지 평가합니다.</p><p>소요 시간은 약 30분이며, 중간에 휴식이 있습니다.</p>",
           "<p>この実験では、コンサートホールの客席に座って公演を聴く状況をヘッドホンで再現します。舞台上ではソプラノ歌手がオーケストラと共に歌い、ソプラノの声は舞台の両脇のスピーカー（PA）で補強されています。</p><p>皆さんは客席の3つの席（左・中央・右）に順番に座り、ソプラノの歌声がどのように聞こえるかを評価します。</p><p>所要時間は約30分で、途中に休憩があります。</p>",
           "<p>In this experiment, headphones recreate listening to a performance from a seat in a concert hall. On stage, a soprano sings with an orchestra, and the soprano's voice is reinforced through loudspeakers (PA) on both sides of the stage.</p><p>You will sit in three seats in the audience (left, centre, right) in turn and rate how the soprano's singing sounds.</p><p>The experiment takes about 30 minutes, with breaks.</p>"),
 "consent": ("<p><b>참여 동의</b></p><ul><li>참여는 자유이며, 언제든지 그만둘 수 있습니다. 그만두어도 불이익은 없습니다.</li><li>이름 등 개인을 알 수 있는 정보는 수집하지 않습니다. 응답은 참가자 코드로만 기록됩니다.</li><li>기록되는 내용: 평가 응답, 듣는 데 걸린 시간, 헤드폰 기종, 브라우저 종류.</li><li>결과는 연구 목적으로만 사용되며, 학회 발표나 논문에는 통계 처리된 형태로 실립니다.</li></ul>",
             "<p><b>参加への同意</b></p><ul><li>参加は自由で、いつでも中止できます。中止しても不利益はありません。</li><li>氏名など個人を特定できる情報は収集しません。回答は参加者コードのみで記録されます。</li><li>記録される内容：評価の回答、聴取にかかった時間、ヘッドホンの機種、ブラウザーの種類。</li><li>結果は研究目的にのみ使用され、学会発表や論文には統計処理した形で掲載されます。</li></ul>",
             "<p><b>Consent</b></p><ul><li>Taking part is voluntary and you may stop at any time, without any disadvantage.</li><li>No information that identifies you, such as your name, is collected. Answers are stored under a participant code only.</li><li>What is recorded: your ratings, listening times, headphone model and browser type.</li><li>The results are used for research only and appear in presentations and papers in statistical form.</li></ul>"),
 "consentCheck": ("위 내용을 읽었으며, 참여에 동의합니다.", "上記の内容を読み、参加に同意します。", "I have read the above and agree to take part."),
 "credits": ("홀 모델·홀 사진: BRAS (Aspöck et al., 2020, CC BY-SA 4.0), 측면 하부·객석·무대 위 인물은 재구성. 음악: Aalto 무향 녹음 (Pätynen, Pulkki & Lokki, 2008). 인물: MetaHuman (Epic Games).",
             "ホールモデル・ホール写真：BRAS（Aspöck et al., 2020, CC BY-SA 4.0）。側面下部・客席・舞台上の人物は再構成。音楽：Aalto無響録音（Pätynen, Pulkki & Lokki, 2008）。人物：MetaHuman（Epic Games）。",
             "Hall model and photograph: BRAS (Aspöck et al., 2020, CC BY-SA 4.0); lower side walls, seats and performers reconstructed. Music: Aalto anechoic recordings (Pätynen, Pulkki & Lokki, 2008). Characters: MetaHuman (Epic Games)."),
 "pid": ("참가자 코드", "参加者コード", "Participant code"),

 "hpH": ("헤드폰 안내", "ヘッドホンについて", "Headphones"),
 "hp": ("<ul><li><b>유선 헤드폰만</b> 사용해 주십시오. 무선 이어폰·헤드폰(블루투스)은 사용할 수 없습니다.</li><li>공간 음향(Spatial Audio), 음향 효과, 이퀄라이저(EQ), 노이즈 캔슬링 기능은 모두 꺼 주십시오.</li><li>조용한 곳에서 참여해 주십시오.</li></ul>",
        "<ul><li><b>有線のヘッドホンのみ</b>を使用してください。ワイヤレス（Bluetooth）のイヤホン・ヘッドホンは使用できません。</li><li>空間オーディオ、音響効果、イコライザー（EQ）、ノイズキャンセリングの機能はすべてオフにしてください。</li><li>静かな場所で参加してください。</li></ul>",
        "<ul><li>Please use <b>wired headphones only</b>. Wireless (Bluetooth) earphones or headphones cannot be used.</li><li>Turn off spatial audio, sound effects, equaliser (EQ) and noise cancelling.</li><li>Please take part in a quiet place.</li></ul>"),
 "hpModel": ("사용하는 헤드폰의 제조사와 모델명", "使用するヘッドホンのメーカーと型番", "Headphone make and model"),
 "hpCheck": ("유선 헤드폰을 사용하고 있으며, 위의 기능을 모두 껐습니다.", "有線ヘッドホンを使用しており、上記の機能をすべてオフにしました。", "I am using wired headphones and have turned off all of the functions above."),

 "lrH": ("좌우 확인", "左右の確認", "Left–right check"),
 "lr": ("버튼을 누르면 한쪽 귀에서만 소리가 납니다. 들린 쪽을 골라 주십시오.", "ボタンを押すと、片方の耳だけから音が出ます。聞こえた側を選んでください。", "Press the button; a sound will play in one ear only. Choose the side you heard."),
 "left": ("왼쪽", "左", "Left"), "right": ("오른쪽", "右", "Right"),
 "lrWrong": ("헤드폰을 좌우 바꿔 착용했는지 확인해 주십시오. 처음부터 다시 확인합니다.", "ヘッドホンの左右が逆になっていないか確認してください。最初からもう一度確認します。", "Please check that the headphones are not worn the wrong way round. The check starts again."),
 "lrOk": ("확인되었습니다.", "確認できました。", "Confirmed."),

 "volH": ("음량 맞추기", "音量の調整", "Volume setting"),
 "vol": ("<p>이제부터 들을 소리 가운데 가장 큰 소리와 같은 크기의 음악이 반복해서 재생됩니다.</p><p><b>충분히 크지만 불편하지 않은 크기</b>가 되도록 컴퓨터(또는 헤드폰)의 볼륨을 맞춰 주십시오.</p><p>맞춘 뒤에는 실험이 끝날 때까지 <b>볼륨을 바꾸지 마십시오.</b> 실험 중 소리의 크기가 조건마다 달라지는 것은 의도된 것입니다.</p>",
         "<p>これから聞く音の中で最も大きい音と同じ大きさの音楽が、繰り返し再生されます。</p><p><b>十分に大きく、かつ不快ではない大きさ</b>になるように、コンピューター（またはヘッドホン）の音量を調整してください。</p><p>調整した後は、実験が終わるまで<b>音量を変えないでください。</b>実験中に条件によって音の大きさが変わるのは、意図されたものです。</p>",
         "<p>Music as loud as the loudest sound in this experiment will play repeatedly.</p><p>Adjust the volume of your computer (or headphones) so that it is <b>clearly loud but not uncomfortable</b>.</p><p>After that, <b>do not change the volume</b> until the end of the experiment. Differences in loudness between sounds during the experiment are intended.</p>"),
 "volDone": ("볼륨을 맞췄습니다", "音量を調整しました", "I have set the volume"),

 "insH": ("평가 방법", "評価の方法", "How to rate"),
 "ins": ("<p>각 소리를 들은 뒤 세 가지를 평가합니다. <b>평가하는 것은 소프라노의 노래(목소리)뿐입니다.</b> 오케스트라 반주는 판단에 넣지 마십시오. 답은 1~5 중에서 고릅니다.</p>"
         "<p><b>질문 1. 방향 — 노래가 가수 위치에서 들렸나요?</b><br>노래가 들린 위치가 무대 위 가수와 스피커 사이에서 어디쯤이었는지 고릅니다. 가수 위치면 5, 스피커 쪽이면 1, 그 사이면 가까운 정도에 맞게 2~4를 고릅니다.<br>왼쪽·오른쪽 자리에서는 무대가 비스듬히 보입니다. <b>지금 앉아 있는 자리에서 본 가수의 위치</b>를 기준으로 판단해 주십시오.<br>위치를 판단하기 어려웠다면 가장 가깝다고 느낀 숫자를 고른 뒤 <b>'판단하기 어려웠다'</b>에도 표시해 주십시오.</p>"
         "<p><b>질문 2. 음색 — 기준음과 비교해 목소리가 자연스러웠나요?</b><br>각 자리에서 처음 들은 기준음(확성하지 않은 소리)과 비교해, 목소리가 겹쳐 들리거나 메아리처럼 들리는 등 부자연스러운 점이 있었는지 판단합니다. 소리의 크기는 판단에 넣지 마십시오.</p>"
         "<p><b>질문 3. 안정성 — 노래가 한 점에 또렷하게 모여 들렸나요?</b><br>소리가 <b>어디에서 들렸는지와 관계없이</b>, 한 점에 또렷하게 모여 있었는지를 판단합니다. 둘로 갈라지거나 넓게 번져 들렸다면 낮게 평가합니다.</p>"
         "<table class='grid'><tr><th></th><th>한 점에 모임<br>(질문 3 높음)</th><th>갈라짐·번짐<br>(질문 3 낮음)</th></tr><tr><th>가수 위치<br>(질문 1 높음)</th><td>가수 위치에 또렷이 들린다</td><td>대체로 가수 쪽이지만 갈라지거나 번진다</td></tr><tr><th>스피커 쪽<br>(질문 1 낮음)</th><td>스피커 쪽에 또렷이 들린다</td><td>스피커 쪽에서 갈라지거나 번진다</td></tr></table>"
         "<p>예를 들어 노래가 <b>스피커 쪽에서 또렷하게</b> 들렸다면, 질문 1은 낮게, 질문 3은 높게 평가합니다.</p>",
         "<p>各音を聞いた後、3つの項目を評価します。<b>評価するのはソプラノの歌（声）だけです。</b>オーケストラの伴奏は判断に含めないでください。回答は1〜5から選びます。</p>"
         "<p><b>質問1. 方向 — 歌は歌手の位置から聞こえましたか。</b><br>歌が聞こえた位置が、舞台上の歌手とスピーカーの間のどのあたりだったかを選びます。歌手の位置なら5、スピーカー側なら1、その間なら近さに応じて2〜4を選びます。<br>左・右の席からは舞台が斜めに見えます。<b>今座っている席から見た歌手の位置</b>を基準に判断してください。<br>位置の判断が難しかった場合は、最も近いと感じた数字を選んだうえで、<b>「判断が難しかった」</b>にも印を付けてください。</p>"
         "<p><b>質問2. 音色 — 基準音と比べて、声は自然でしたか。</b><br>各席で最初に聞いた基準音（拡声していない音）と比べて、声が二重に聞こえる、こだまのように聞こえるなど、不自然な点があったかを判断します。音の大きさは判断に含めないでください。</p>"
         "<p><b>質問3. 安定性 — 歌は一点にはっきりまとまって聞こえましたか。</b><br>音が<b>どこから聞こえたかとは関係なく</b>、一点にはっきりまとまっていたかを判断します。二つに分かれたり、広くにじんだりして聞こえた場合は低く評価します。</p>"
         "<table class='grid'><tr><th></th><th>一点にまとまる<br>（質問3 高い）</th><th>分かれる・にじむ<br>（質問3 低い）</th></tr><tr><th>歌手の位置<br>（質問1 高い）</th><td>歌手の位置にはっきり聞こえる</td><td>おおむね歌手側だが、分かれたりにじんだりする</td></tr><tr><th>スピーカー側<br>（質問1 低い）</th><td>スピーカー側にはっきり聞こえる</td><td>スピーカー側で分かれたりにじんだりする</td></tr></table>"
         "<p>例えば、歌が<b>スピーカー側からはっきり</b>聞こえた場合は、質問1を低く、質問3を高く評価します。</p>",
         "<p>After each sound, you will answer three questions. <b>Rate only the soprano's singing (voice).</b> Do not take the orchestral accompaniment into account. Each answer is a number from 1 to 5.</p>"
         "<p><b>Question 1. Direction — Did the singing come from the singer's position?</b><br>Choose where, between the singer on stage and the loudspeaker, the singing seemed to come from: 5 for the singer's position, 1 for the loudspeaker, and 2–4 for positions in between.<br>From the left and right seats the stage is seen at an angle. Judge relative to <b>where the singer is as seen from the seat you are in now</b>.<br>If the position was hard to judge, choose the number that seemed closest and also tick <b>'Hard to judge'</b>.</p>"
         "<p><b>Question 2. Timbre — Compared with the reference, did the voice sound natural?</b><br>Compared with the reference sound you heard first at each seat (the sound without amplification), judge whether anything sounded unnatural, for example the voice sounding doubled or echo-like. Do not take loudness into account.</p>"
         "<p><b>Question 3. Stability — Did the singing sound clearly gathered at one point?</b><br><b>Regardless of where it came from</b>, judge whether the sound was clearly gathered at one point. If it split in two or was spread widely, rate it low.</p>"
         "<table class='grid'><tr><th></th><th>At one point<br>(Q3 high)</th><th>Split / spread<br>(Q3 low)</th></tr><tr><th>Singer's position<br>(Q1 high)</th><td>Clearly at the singer</td><td>Mostly towards the singer, but splits or spreads</td></tr><tr><th>Loudspeaker<br>(Q1 low)</th><td>Clearly at the loudspeaker</td><td>Towards the loudspeaker, split or spread</td></tr></table>"
         "<p>For example, if the singing came <b>clearly from a loudspeaker</b>, rate Question 1 low and Question 3 high.</p>"),

 "qzH": ("이해 확인", "理解の確認", "Check your understanding"),
 "qz": ("본 실험 전에, 질문의 뜻을 바르게 이해했는지 확인합니다. 각 상황에서 어떻게 답하면 되는지 골라 주십시오. 소리는 나오지 않습니다.", "本実験の前に、質問の意味を正しく理解しているかを確認します。それぞれの状況でどのように答えればよいかを選んでください。音は出ません。", "Before the main part, let us check that the questions are clear. For each situation, choose how you should answer. No sound is played."),
 "qz1": ("노래가 스피커 쪽에서 들렸지만, 한 점에 또렷하게 모여 있었습니다.", "歌はスピーカー側から聞こえましたが、一点にはっきりまとまっていました。", "The singing came from the loudspeaker, but it was clearly gathered at one point."),
 "qz2": ("노래가 가수 위치에서 들렸지만, 둘로 갈라지거나 넓게 번져 들렸습니다.", "歌は歌手の位置から聞こえましたが、二つに分かれたり、広くにじんだりして聞こえました。", "The singing came from the singer's position, but it split in two or was spread widely."),
 "qz3": ("기준음보다 소리가 조금 크게 들렸지만, 목소리가 겹치거나 메아리처럼 들리지는 않았습니다. 질문 2는?", "基準音より音が少し大きく聞こえましたが、声が二重やこだまのように聞こえることはありませんでした。質問2は？", "The sound was a little louder than the reference, but the voice did not sound doubled or echo-like. Question 2?"),
 "qzHL": ("질문 1 낮게, 질문 3 높게", "質問1を低く、質問3を高く", "Question 1 low, Question 3 high"),
 "qzLH": ("질문 1 높게, 질문 3 낮게", "質問1を高く、質問3を低く", "Question 1 high, Question 3 low"),
 "qzHH": ("질문 1 높게, 질문 3 높게", "質問1を高く、質問3を高く", "Question 1 high, Question 3 high"),
 "qzLL": ("질문 1 낮게, 질문 3 낮게", "質問1を低く、質問3を低く", "Question 1 low, Question 3 low"),
 "qz3a": ("높게 (자연스러웠다)", "高く（自然だった）", "High (natural)"),
 "qz3b": ("낮게 (소리가 커졌으므로)", "低く（音が大きくなったので）", "Low (because it was louder)"),
 "qz1why": ("질문 1은 위치(가수인지 스피커인지), 질문 3은 한 점에 모였는지를 묻습니다. 스피커 쪽이므로 질문 1은 낮게, 한 점에 모였으므로 질문 3은 높게 답합니다.", "質問1は位置（歌手かスピーカーか）、質問3は一点にまとまっていたかを問います。スピーカー側なので質問1は低く、一点にまとまっていたので質問3は高く答えます。", "Question 1 asks about position (singer or loudspeaker); Question 3 asks whether the sound was gathered at one point. It came from the loudspeaker, so Question 1 is low; it was at one point, so Question 3 is high."),
 "qz2why": ("가수 위치이므로 질문 1은 높게, 갈라지거나 번졌으므로 질문 3은 낮게 답합니다. 위치와 모임 정도는 따로 판단합니다.", "歌手の位置なので質問1は高く、分かれたりにじんだりしたので質問3は低く答えます。位置とまとまりは別々に判断します。", "It came from the singer, so Question 1 is high; it split or spread, so Question 3 is low. Position and gathering are judged separately."),
 "qz3why": ("소리의 크기는 질문 2에서 판단하지 않습니다. 겹침이나 메아리가 없었다면 높게 답합니다.", "音の大きさは質問2では判断しません。二重やこだまがなければ高く答えます。", "Loudness is not part of Question 2. If there was no doubling or echo, answer high."),
 "qzCheck": ("확인", "確認", "Check"), "qzRetry": ("다시 확인", "もう一度確認", "Check again"),
 "trialHint": ("소리는 자동으로 재생됩니다. 들으면서 바로 답할 수 있고, {s}초 이상 들으면 다음으로 넘어갈 수 있습니다. 다시 들을 수도 있습니다.", "音は自動的に再生されます。聞きながらすぐに回答でき、{s}秒以上聞くと次に進めます。もう一度聞くこともできます。", "The sound starts by itself. You can answer while listening and go on after {s} seconds. You may listen again."),
 "q1": ("질문 1. 방향: 노래가 가수 위치에서 들렸나요?", "質問1. 方向：歌は歌手の位置から聞こえましたか。", "Question 1. Direction: Did the singing come from the singer's position?"),
 "q1a": ("스피커 쪽에서 들렸다", "スピーカー側から聞こえた", "From the loudspeaker"), "q1b": ("가수 위치에서 들렸다", "歌手の位置から聞こえた", "From the singer"),
 "q1dk": ("판단하기 어려웠다", "判断が難しかった", "Hard to judge"),
 "q2": ("질문 2. 음색: 기준음과 비교해 목소리가 자연스러웠나요?", "質問2. 音色：基準音と比べて、声は自然でしたか。", "Question 2. Timbre: Compared with the reference, did the voice sound natural?"),
 "q2a": ("겹치거나 메아리처럼 들렸다", "二重やこだまのように聞こえた", "Doubled or echo-like"), "q2b": ("자연스러웠다", "自然だった", "Natural"),
 "q3": ("질문 3. 안정성: 노래가 한 점에 또렷하게 모여 들렸나요?", "質問3. 安定性：歌は一点にはっきりまとまって聞こえましたか。", "Question 3. Stability: Did the singing sound clearly gathered at one point?"),
 "q3a": ("갈라지거나 넓게 번졌다", "分かれたり、広くにじんだりした", "Split or spread"), "q3b": ("한 점에 또렷이 모였다", "一点にはっきりまとまった", "Clearly at one point"),
 "progress": ("{seat} 자리 · {n} / {of}", "{seat}の席 · {n} / {of}", "{seat} seat · {n} / {of}"),
 "practiceTag": ("연습 {n} / {of} · {seat} 자리", "練習 {n} / {of} · {seat}の席", "Practice {n} / {of} · {seat} seat"),

 "pracH": ("연습", "練習", "Practice"),
 "prac": ("본 실험 전에 연습으로 4개의 소리를 들어 봅니다. 평가 방법에 익숙해지기 위한 것이며, 결과는 기록되지 않습니다. 연습에서 듣는 소리는 본 실험과 다른 구간의 음악입니다.", "本実験の前に、練習として4つの音を聞きます。評価の方法に慣れるためのもので、結果は記録されません。練習で聞く音は、本実験とは別の区間の音楽です。", "Before the main part, you will hear four sounds for practice. This is to get used to rating; the answers are not recorded. The practice sounds use a different passage of the music from the main part."),
 "pracEnd": ("연습이 끝났습니다. 이제 본 실험을 시작합니다.", "練習が終わりました。これから本実験を始めます。", "Practice is finished. The main part starts now."),

 "seatH": ("{seat} 자리입니다.", "{seat}の席です。", "You are in the {seat} seat."),
 "seatView": ("화면은 이 자리에서 본 무대 모습입니다.", "画面は、この席から見た舞台の様子です。", "The picture shows the stage as seen from this seat."),
 "seatRef": ("먼저 <b>기준음</b>을 한 번 들려드립니다. 이 자리에서 들리는, <b>확성하지 않은 소리</b>입니다. 질문 2(음색)를 판단할 때 참고해 주십시오. 기준음은 이 자리에서 한 번만 재생됩니다.", "まず<b>基準音</b>を一度お聞かせします。この席で聞こえる、<b>拡声していない音</b>です。質問2（音色）を判断する際の参考にしてください。基準音は、この席では一度だけ再生されます。", "First you will hear the <b>reference sound</b> once. It is the sound at this seat <b>without amplification</b>. Use it as a reference for Question 2 (timbre). The reference plays only once at this seat."),
 "seatCount": ("이어서 이 자리에서 {count}개의 소리를 평가합니다.", "続いて、この席で{count}個の音を評価します。", "Then you will rate {count} sounds at this seat."),
 "refPlay": ("기준음 재생", "基準音を再生", "Play the reference"), "refPlaying": ("기준음 재생 중…", "基準音を再生中…", "Playing the reference…"),

 "stage0": ("준비", "準備", "Setup"), "stage1": ("안내", "説明", "Instructions"), "stage2": ("연습", "練習", "Practice"), "stage3": ("본 실험", "本実験", "Main part"), "stage4": ("마무리", "終了", "Finish"),
 "brkDone": ("{seat} 자리가 끝났습니다", "{seat}の席が終わりました", "The {seat} seat is finished"),
 "brkNextN": ("다음 · {count}개", "次 · {count}個", "Next · {count} sounds"), "brkN": ("{count}개", "{count}個", "{count} sounds"),
 "breakH": ("휴식", "休憩", "Break"),
 "brk": ("잠시 쉬어 주십시오. 준비가 되면 다음 자리로 이동합니다. <b>볼륨은 바꾸지 마십시오.</b>", "少し休憩してください。準備ができたら、次の席に移ります。<b>音量は変えないでください。</b>", "Please take a short break. When you are ready, you will move to the next seat. <b>Do not change the volume.</b>"),
 "brkNext": ("다음 자리로", "次の席へ", "Go to the next seat"),

 "postH": ("마지막 질문", "事後アンケート", "Final questions"),
 "p1": ("질문 1(방향)과 질문 3(안정성)을 구분해서 판단하기 어려웠습니까?", "質問1（方向）と質問3（安定性）を区別して判断するのは難しかったですか。", "Was it difficult to tell Question 1 (direction) and Question 3 (stability) apart?"),
 "pLo": ("전혀 아니다", "全くそう思わない", "Not at all"), "pHi": ("매우 그렇다", "非常にそう思う", "Very much"),
 "p2": ("노래가 불안정하게 들렸을 때, 주로 어떻게 들렸습니까? (해당하는 것을 모두 선택)", "歌が不安定に聞こえたとき、主にどのように聞こえましたか。（当てはまるものをすべて選択）", "When the singing sounded unstable, how did it mainly sound? (choose all that apply)"),
 "p2a": ("둘로 갈라짐", "二つに分かれた", "Split in two"), "p2b": ("위치가 움직임", "位置が動いた", "Moved"), "p2c": ("넓게 번짐", "広くにじんだ", "Spread widely"), "p2d": ("기타", "その他", "Other"),
 "p3": ("실험 중 피로를 느꼈습니까?", "実験中に疲れを感じましたか。", "Did you feel tired during the experiment?"),
 "p4": ("음악 또는 음향 관련 경력(전공·직업 포함, 년)", "音楽または音響に関する経験（専攻・職業を含む、年）", "Years of experience in music or audio (including study and work)"),
 "p5": ("청력에 이상을 느끼고 있습니까?", "聴覚に異常を感じていますか。", "Do you notice any problems with your hearing?"),
 "yes": ("예", "はい", "Yes"), "no": ("아니오", "いいえ", "No"), "dk": ("모르겠다", "分からない", "Don't know"),
 "p6": ("기타 의견", "その他のご意見", "Other comments"),
 "submit": ("제출", "送信", "Submit"),

 "endH": ("종료", "終了", "End"),
 "sending": ("결과를 전송하는 중입니다…", "結果を送信しています…", "Sending your answers…"),
 "endOk": ("참여해 주셔서 감사합니다. 결과가 전송되었습니다.", "ご参加いただき、ありがとうございました。結果は送信されました。", "Thank you for taking part. Your answers have been sent."),
 "endFail": ("참여해 주셔서 감사합니다. 결과를 전송하지 못했습니다. 아래 버튼으로 결과 파일을 내려받아 실험자에게 보내 주십시오.", "ご参加いただき、ありがとうございました。結果を送信できませんでした。下のボタンで結果ファイルをダウンロードし、実験者に送ってください。", "Thank you for taking part. Your answers could not be sent. Please download the results file with the button below and send it to the experimenter."),
 "download": ("결과 파일 내려받기", "結果ファイルをダウンロード", "Download results file"),
}
here = os.path.dirname(os.path.abspath(__file__))
for i, lang in enumerate(("ko", "ja", "en")):
    json.dump({k: v[i] for k, v in T.items()}, open(os.path.join(here, "..", "web", "i18n", lang + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(T), "keys x 3 languages")
