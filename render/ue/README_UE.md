# CR3 좌석 시점 그림: Unreal Engine 5 + MetaHuman 작업 순서

목표: 실험 사이트의 좌석 화면에 쓸 정지 이미지 3장(`seat_L`, `seat_C`, `seat_R`, 2560×1440)을 UE에서 렌더링한다.
홀·소품·카메라·위치는 이 폴더에 다 들어 있다. 사람(MetaHuman)을 만들어 자세를 잡는 일만 UE 안에서 직접 한다.

**UE 5.8.4 기준.** 메뉴 이름이 조금 다르면 스크린샷을 보내줘.

## 0. 이 폴더의 파일

| 파일 | 내용 | UE에서의 재질 |
|---|---|---|
| `CR3_hall.fbx` + `T_CR3_hall_0…7.png` | 벽·천장·발코니·무대 안쪽. BRAS 360° 사진을 촬영 지점에서 투영해 텍스처로 새긴 것(조각 8개) | **Emissive**(빛나는 사진, 3절) |
| `CR3_stagefloor.fbx` + `T_CR3_stagefloor.png` | 무대 바닥(높이 100 cm). 사람 그림자가 떨어져야 해서 따로 뺌 | 일반(Lit) |
| `CR3_audiencefloor.fbx` + `T_parquet.jpg` | 1층 객석 바닥(쪽모이). 텍스처 1장 = 1.2 m | 일반(Lit) |
| `CR3_audience_chairs.fbx` | 1층 객석 의자 195개(아이보리 틀, 청록 벨벳, 좌석 접힘) | 일반 |
| `CR3_PA.fbx` | PA 스피커 2대 + 스탠드(자극과 같은 위치, 가정) | 일반 |
| `CR3_stage_props.fbx` | 연주자 의자, 보면대 | 일반 |
| `CR3_instruments.fbx` | 악기와 활. Blender 임시 인물이 들고 있던 위치(출발점일 뿐, MetaHuman 손에 맞게 옮김) | 일반 |
| `CR3_markers_cameras.fbx` | 좌석 카메라 3대, 연주자 11명 바닥 표시(주황 화살표 = 몸이 향하는 방향), 축 확인 막대 | 표시용(렌더 전에 숨김) |
| `layout_ue.csv` | 위 위치들의 숫자(UE 좌표, cm, 회전) | |
| `ref_seat_L/C/R.png` | 사람 없이 Blender에서 그린 참고 화면. UE 결과의 밝기·구도를 맞출 때 비교용 | |

## 1. 설치와 프로젝트

1. Epic Games Launcher에서 **5.8.4** 설치. 설치 중이거나 이미 설치했다면 Launcher의 라이브러리에서 5.8 타일의 **▼ → Options**를 열고 **MetaHuman Creator Core Data**를 켠 뒤 Apply. 이 데이터가 없으면 MetaHuman Creator를 켤 때 경고가 뜨고 사람을 만들 수 없다.
2. 새 프로젝트: **Film / Video & Live Events → Blank**, Starter Content 없음. 이름 예: `CR3_Pilot2`. 위치는 iCloud 폴더가 아닌 로컬 디스크(예: `~/Documents/Unreal Projects`)를 권장. 프로젝트는 수십 GB까지 커지고, iCloud 동기화와 충돌할 수 있다.
3. Edit → Plugins:
   - `MetaHuman`으로 검색 → **MetaHuman Creator** 켬(베타라는 안내가 뜨면 확인).
   - `Movie Render`로 검색 → **Movie Render Queue**가 켜져 있는지 확인(5.8의 렌더 화면인 Movie Render Graph가 이 플러그인에 들어 있다).
   - 에디터 재시작.
4. Project Settings → Rendering:
   - Global Illumination = **Lumen**, Reflections = **Lumen**(기본값).
   - 5.8에 새로 생긴 **Lumen Lite는 쓰지 않는다**(게임용 중간 품질). Lumen 품질은 높게 둔다.
   - M1이라 Hardware Ray Tracing은 켜지 않는다.
   - MegaLights는 켤 필요 없다(조명이 5개뿐).

## 2. 가져오기

1. File → New Level → **Empty Level**. 저장(`CR3`).
2. File → **Import Into Level…** → `CR3_hall.fbx` 선택. 옵션에서 크기(Uniform Scale)는 1.0 그대로. 나머지 FBX도 같은 방법으로 하나씩 가져온다.
3. **축 확인**: `AXIS_plus_x_to_audience`(빨강 1 m)가 객석 쪽을 가리키고, `AXIS_plus_y_right_seen_from_audience`(초록 1 m)가 **객석에서 무대를 볼 때 오른쪽**을 가리켜야 한다. 반대로 보이면 가져오기를 멈추고 스크린샷을 보내줘(좌우가 뒤집히면 자극의 L/R과 화면이 어긋난다).
4. 크기 확인: 무대 바닥 높이 100 cm, 좌석 카메라 높이 123 cm(`layout_ue.csv`와 같은지).

## 3. 재질

**홀 사진(`CR3_hall`)**: 사진이 그대로 보이고 그 빛이 사람을 비추도록 Emissive로 만든다.
1. 콘텐츠 브라우저에서 새 Material `M_HallPhoto` 생성 → Details에서 **Shading Model = Unlit**.
2. Texture Sample 노드를 **Texture Parameter**로 바꾸고(이름 `Photo`) → **Emissive Color**에 연결. 저장.
3. `M_HallPhoto`를 우클릭 → Create Material Instance를 8개(`MI_HallPhoto_0…7`) 만들고, 각각 `Photo`에 `T_CR3_hall_0…7`을 지정.
4. 레벨의 `CR3_hall` 조각 8개에 같은 번호의 인스턴스를 지정한다(조각 이름 끝 번호 = 텍스처 번호).
5. Lumen이 Emissive를 간접광으로 쓰므로 사람에게 홀의 따뜻한 빛이 들어간다.

**무대 바닥·객석 바닥**: 가져올 때 만들어진 재질에 텍스처가 Base Color로 들어가 있는지 확인. Roughness 0.4–0.5.

**의자·스피커·악기**: 가져온 재질 그대로 써도 된다. 벨벳은 Base Color를 진한 청록(약 #0B1B22)으로.

## 4. 노출과 조명

1. **Post Process Volume** 추가 → Infinite Extent(Unbound) 켬 → Exposure: Metering Mode = **Manual**, Exposure Compensation으로 홀이 `ref_seat_C.png`와 비슷한 밝기가 되게 맞춘다(사진이 기준).
2. 무대 조명(사진에 보이는 객석 쪽 천장 트러스 위치): **Spot Light 4개**. 위치(cm)·조준점은 아래 표. 색온도 약 3200 K, Inner/Outer Cone 약 15°/21°, Source Radius 25. 세기는 가수 얼굴이 무대 흰 벽보다 약간 어둡게 보일 때까지 조절.

| 조명 | X | Y | Z | 조준점 X, Y, Z |
|---|---|---|---|---|
| Spot 1 | 120 | 300 | 660 | −500, 165, 150 |
| Spot 2 | 120 | 100 | 660 | −500, 55, 150 |
| Spot 3 | 120 | −100 | 660 | −500, −55, 150 |
| Spot 4 | 120 | −300 | 660 | −500, −165, 150 |

3. 무대 위 넓은 빛: **Rect Light** 1개, 위치 (−550, 0, 680), 아래를 향하게, 크기 600×600 cm, 따뜻한 흰색.

## 5. 카메라 (바꾸지 말 것)

`SeatCam_L/C/R`은 BRIR을 만든 귀 위치와 머리 방향 그대로다. 그림이 소리와 맞으려면 이 값이 그대로여야 한다.

| 카메라 | X | Y | Z | 회전(Yaw) | 시야 |
|---|---|---|---|---|---|
| SeatCam_L | 784 | 400 | 123 | 180° | 가로 94° |
| SeatCam_C | 784 | 0 | 123 | 180° | 가로 94° |
| SeatCam_R | 784 | −400 | 123 | 180° | 가로 94° |

CineCamera라면 Filmback 36 × 20.25 mm(16:9), Focal Length **16.79 mm**, Pitch 0, Roll 0. 가져온 카메라가 이 값과 다르면 표 값으로 고친다.

## 6. MetaHuman 만들기 (11명)

| 이름 | 역할 | 자세 | 제안 |
|---|---|---|---|
| Singer | 소프라노(확성되는 소리, 경로 A) | 서서, 두 손 모음 | 여성, 긴 진청색 드레스 |
| ViolinI, ViolinII | 바이올린 | 앉아서 | 남·여 섞어서 |
| Viola, Cello | 비올라, 첼로 | 앉아서 | |
| Contrabass | 콘트라베이스 | 서서 | |
| Flute, Clarinet, Bassoon | 목관 | 앉아서 | |
| Horn1, Horn2 | 호른 | 앉아서 | |

- 옷: 연주자는 검은 정장. MetaHuman Creator의 의상 중 가장 어두운 정장을 고르고 색을 검정으로.
- **머리카락은 Cards 방식**: M1에서는 strands(한 올씩 그리는 방식)가 렌더되지 않는다. 연주자는 약 12 m 거리라 차이가 거의 없다.
- 얼굴은 너무 비슷하지 않게 여러 개를 섞는다.

## 7. 배치와 자세 (가장 오래 걸리는 단계)

1. 각 MetaHuman을 `layout_ue.csv`의 `UE_X_cm, UE_Y_cm, UE_Z_floor_cm`(무대 바닥 100 cm)에 놓고 `UE_yaw_deg`만큼 돌린다. 주황 화살표 끝이 얼굴이 향하는 방향이다.
2. **Level Sequence**를 하나 만들고(`LS_Seats`) MetaHuman을 모두 넣는다. 몸에 Control Rig가 붙으면 FK/IK 컨트롤로 자세를 잡고 프레임 0에 키를 넣는다.
3. 앉은 사람: 골반을 의자 높이(바닥 + 45 cm)까지 내리고 무릎을 굽힌다. `CR3_stage_props`의 의자에 맞춘다.
4. 악기: `CR3_instruments`의 악기를 손 위치에 맞게 옮기고 돌린다. 기준은 다음과 같다.
   - 바이올린·비올라: 왼쪽 어깨와 턱 사이, 왼손은 스크롤 쪽, 오른손은 활.
   - 첼로: 무릎 사이, 엔드핀은 바닥.
   - 플루트: 입에서 오른쪽 가로. 클라리넷: 입에서 앞아래. 바순: 몸 오른쪽 앞에서 비스듬히. 호른: 오른쪽 허벅지 위.
5. 우선순위: 가수 → 앞줄(바이올린 I, 첼로, 비올라) → 뒷줄. 뒷줄은 보면대에 가려 손이 잘 안 보인다.
6. 막히면 좌석 카메라에서 본 스크린샷을 보내줘. 각도를 봐줄게.

## 8. 렌더링 (5.8: Movie Render Graph)

1. 렌더 전에 `MARK_*`와 `AXIS_*`는 숨긴다(Details → Rendering → Actor Hidden In Game, 또는 삭제).
2. `LS_Seats`에 Camera Cut 트랙을 넣고 카메라를 `SeatCam_C`로 지정(길이 1프레임). L, R은 시퀀스를 복제해 카메라만 바꾼다(`LS_Seat_L`, `LS_Seat_C`, `LS_Seat_R`).
3. Window → Cinematics → **Movie Render Queue** → 시퀀스 3개 추가. 5.8에서는 Queue 창에서 바로 그래프 방식 설정(Movie Render Graph)을 고를 수 있다. 기본 그래프 설정을 하나 만들어 세 시퀀스에 같이 쓴다:
   - Output: **2560 × 1440**, PNG(8-bit), 파일 이름 `seat_{L|C|R}`.
   - Anti-aliasing: Temporal Sample Count **16**(높을수록 깨끗, 느림), Spatial Sample Count 1.
   - Warm Up Frames(Engine Warm Up Count) **64 이상**(Lumen이 안정될 시간).
   - 그래프 설정이 어려우면 예전 방식(Legacy)의 Movie Render Queue 설정을 써도 같은 결과가 나온다.
4. Render(Local). M1 Max에서 1장에 몇 분 걸릴 수 있다.

## 9. 보내줄 것

- `seat_L.png`, `seat_C.png`, `seat_R.png`(2560 × 1440).
- 받으면 내가 사이트(`web/img/seat_*.jpg`)에 넣고 점검한다.

## 주의

- 카메라 위치·방향·시야(5절)와 사람·스피커 위치(7절)는 자극과 같아야 한다. 보기 좋게 바꾸고 싶으면 먼저 말해줘.
- 화면에 가수가 또렷이 보이면 시각이 정위 판단을 끌어당길 수 있다(Alais & Burr, 2004, https://doi.org/10.1016/j.cub.2004.01.029). 계획서에 "시청각 조건"과 이 한계를 적는다.
- 출처: 홀 모델·사진 BRAS(Aspöck et al., https://doi.org/10.14279/depositonce-6726.3). 온라인 공개 전에 사진 라이선스를 확인하고 사이트에 출처를 적는다.
